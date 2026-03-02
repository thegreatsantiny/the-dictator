#!/usr/bin/env python3
import os
import sys
import json
import time
import tempfile
import threading
import subprocess
import wave
from pathlib import Path
import signal

import numpy as np
import pyaudio
from groq import Groq

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
CORRECTIONS_PATH = Path("~/.config/voice-dictation/corrections.json").expanduser()
PID_PATH = "/tmp/voice-dictation.pid"
LOG_PATH = "/tmp/voice-dictation.log"

def log(msg):
    with open(LOG_PATH, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

def notify(title, message, timeout=3000):
    subprocess.run([
        "notify-send", "-u", "normal", 
        "--expire-time={}".format(timeout),
        title, message
    ], capture_output=True)

def notify_error(title, message):
    subprocess.run([
        "notify-send", "-u", "critical", 
        "--icon=dialog-error", title, message
    ], capture_output=True)


class VoiceDictation:
    def __init__(self):
        self.load_config()
        self.setup_groq()
        self.recording = False
        self.processing = False
        self.audio_data = []
        self.last_toggle = 0
        
        with open(PID_PATH, 'w') as f:
            f.write(str(os.getpid()))
        
        self.check_ydotool()
        
        log("Started")
        
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        notify("Voice Dictation", "Ready! Press Alt+Z to start/stop recording.")
        
        self.wait_for_toggle()
    
    def cleanup(self, *args):
        log("Shutting down")
        try:
            os.unlink(PID_PATH)
        except:
            pass
        sys.exit(0)
    
    def wait_for_toggle(self):
        toggle_file = "/tmp/voice-dictation.toggle"
        
        while True:
            if os.path.exists(toggle_file):
                log(f"[TOGGLE_CHECK] File detected at {time.time()}")
                try:
                    os.unlink(toggle_file)
                except:
                    pass
                
                now = time.time()
                if now - self.last_toggle < 1.0:
                    continue
                self.last_toggle = now
                
                log(f"[TOGGLE_CHECK] Calling handle_toggle at {time.time()}")
                self.handle_toggle()
            time.sleep(0.1)
    
    def handle_toggle(self):
        log(f"[TOGGLE] State: recording={self.recording}, processing={self.processing}, start_time={getattr(self, 'recording_start_time', 'NOT_SET')}")
        
        if self.processing:
            log("[TOGGLE] Skipping - processing")
            return
        
        if self.recording:
            log("[TOGGLE] Stopping recording")
            self.stop_recording()
        else:
            log("[TOGGLE] Starting recording")
            self.start_recording()
    
    def load_config(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "clipboard_copy": True,
                "whisper_model": "whisper-large-v3-turbo",
                "language": "en",
            }
    
    def load_corrections(self):
        corrections_path = Path(self.config.get("corrections_file", str(CORRECTIONS_PATH))).expanduser()
        if corrections_path.exists():
            with open(corrections_path) as f:
                return json.load(f).get("dictionary", {})
        return {}
    
    def setup_groq(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            notify_error("Error", "GROQ_API_KEY not set!")
            sys.exit(1)
        self.groq_client = Groq(api_key=api_key)
    
    def check_ydotool(self):
        result = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True)
        if result.returncode != 0:
            log("Starting ydotoold")
            subprocess.Popen(["ydotoold"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    
    def start_recording(self):
        self.recording = True
        self.recording_start_time = time.time()
        self.audio_data = []
        log(f"[RECORDING] Started at {self.recording_start_time}")
        notify("Recording...", "Press Alt+Z to stop", 15000)
        
        def record():
            try:
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=2,
                    rate=44100,
                    input=True,
                    input_device_index=11,
                    frames_per_buffer=2048
                )
                
                while self.recording:
                    try:
                        data = stream.read(2048, exception_on_overflow=False)
                        if data:
                            self.audio_data.append(data)
                    except:
                        break
                
                stream.stop_stream()
                stream.close()
                p.terminate()
            except Exception as e:
                log(f"Recording error: {e}")
                self.recording = False
        
        threading.Thread(target=record, daemon=True).start()
    
    def stop_recording(self):
        if not self.recording:
            log("[STOP] Not recording, returning")
            return
        
        start_time = getattr(self, 'recording_start_time', None)
        if start_time is None:
            log("[STOP] ERROR - recording_start_time is None!")
            start_time = time.time()
        
        recording_duration = time.time() - start_time
        total_bytes = sum(len(chunk) for chunk in self.audio_data)
        
        log(f"[STOP] Duration: {recording_duration:.1f}s, Audio bytes: {total_bytes}, Chunks: {len(self.audio_data)}")
        
        self.recording = False
        self.processing = True
        
        time.sleep(0.3)
        
        if total_bytes < 8000:
            notify_error("No audio", "Speak louder or check mic")
            self.processing = False
            return
        
        threading.Thread(target=self.process_audio, daemon=True).start()
    
    def process_audio(self):
        start_time = time.time()
        log(f"[TIMING] Processing started at {start_time}")
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                wav_path = f.name
            
            # Convert stereo to mono for Whisper - use numpy for speed
            audio_bytes = b''.join(self.audio_data)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            # Take left channel only (every other sample for stereo)
            mono_np = audio_np[::2]
            mono_audio = mono_np.tobytes()
            
            log(f"[TIMING] Audio converted: {time.time() - start_time:.2f}s")
            
            wf = wave.open(wav_path, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(mono_audio)
            wf.close()
            
            log(f"[TIMING] WAV file created: {time.time() - start_time:.2f}s")
            
            notify("Processing...", "Transcribing", 5000)
            
            whisper_start = time.time()
            with open(wav_path, 'rb') as audio_file:
                text = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.config["whisper_model"],
                    language=self.config["language"],
                    response_format="text"
                )
            
            whisper_time = time.time() - whisper_start
            log(f"[TIMING] Whisper API done: {whisper_time:.2f}s (total: {time.time() - start_time:.2f}s)")
            
            os.unlink(wav_path)
            
            if not isinstance(text, str):
                text = str(text)
            
            text = text.strip()
            if not text:
                notify_error("Empty", "No speech detected")
                self.processing = False
                return
            
            log(f"Whisper raw: {text[:50]}")
            
            # LLM cleanup
            if self.config.get("llm_cleanup", True):
                llm_start = time.time()
                text = self.cleanup_text(text)
                log(f"[TIMING] LLM cleanup done: {time.time() - llm_start:.2f}s (total: {time.time() - start_time:.2f}s)")
            
            text = self.apply_corrections(text)
            
            text = self.apply_corrections(text)
            
            notify("Done!", f'"{text}"', 5000)
            
            clipboard_start = time.time()
            if self.config.get("clipboard_copy", True):
                subprocess.run(["wl-copy"], input=text, text=True)
            log(f"[TIMING] Clipboard done: {time.time() - clipboard_start:.2f}s")
            
            self.type_text(text)
            
            total_time = time.time() - start_time
            log(f"[TIMING] TOTAL: {total_time:.2f}s - Result: {text[:30]}")
            
        except Exception as e:
            log(f"Error: {e}")
            notify_error("Error", str(e)[:40])
        
        finally:
            self.processing = False
    
    def apply_corrections(self, text):
        corrections = self.load_corrections()
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        return text
    
    def cleanup_text(self, text):
        prompt = f"""Your task is to clean up text captured via speech-to-text.

Common STT issues to fix:
- Filler words: um, uh, ah, like, you know, basically, actually, I mean
- Missing punctuation
- Missing capitalization at sentence starts
- Missing spaces between words
- Obvious typos

Examples of corrections:
- "LLAMA 3.2" → "Llama 3.2"
- "five two nine" → "529"
- "um hello I think uh yeah" → "Hello, I think"

Rules:
- Preserve the speaker's voice and tone
- Do NOT add any preamble like "Here's the cleaned text:"
- Do NOT add any suffix or signature
- Return ONLY the cleaned text - nothing else

Text to clean:
{text}"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.config.get("llm_model", "llama-3.1-8b-instant"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            log(f"LLM cleanup error: {e}")
            return text
    
    def type_text(self, text):
        estimated_time = len(text) * 0.012 + 1
        timeout = max(5, min(estimated_time, 30))
        
        try:
            subprocess.run(["ydotool", "type", text], check=True, timeout=timeout)
            log(f"Typed text: {text[:30]}")
        except subprocess.CalledProcessError as e:
            log(f"ydotool failed: {e}")
            notify_error("Typing failed", "ydotool command failed - is ydotoold running?")
        except FileNotFoundError:
            log("ydotool not found")
            notify_error("Typing failed", "ydotool not installed")
        except subprocess.TimeoutExpired:
            log("ydotool timed out, releasing stuck keys")
            for keycode in [58, 42, 29, 56, 54]:
                try:
                    subprocess.run(["ydotool", "key", f"{keycode}:1", f"{keycode}:0"], 
                                  timeout=1, capture_output=True)
                except:
                    pass
            notify_error("Typing timed out", f"Text may be too long ({len(text)} chars)")
        except Exception as e:
            log(f"ydotool failed: {e}")
            notify_error("Typing failed", str(e)[:40])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--toggle", action="store_true")
    args = parser.parse_args()
    
    if args.toggle:
        open("/tmp/voice-dictation.toggle", 'w').write('1')
        sys.exit(0)
    
    if os.path.exists(PID_PATH):
        try:
            with open(PID_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print("Already running!")
            sys.exit(1)
        except:
            pass
    
    VoiceDictation()
