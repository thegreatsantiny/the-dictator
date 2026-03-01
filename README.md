# The Dictator - Voice Dictation for Linux

A hands-free voice dictation system for Linux that transcribes your voice and types it directly into any application.

## Features

- **Voice to Text** - Uses Groq's Whisper API for fast, accurate transcription
- **AI Cleanup** - Uses Groq's Llama LLM to clean up transcription (fixes punctuation, capitalization, filler words)
- **Auto-Typing** - Automatically types the transcribed text into the focused application using ydotool
- **System Notifications** - Shows status notifications during recording, processing, and completion
- **Systemd Service** - Runs as a background service, auto-starts on login

## Requirements

- Linux with PipeWire audio server
- Groq API key (free at groq.com)
- ydotool (for auto-typing)
- wl-clipboard (for clipboard operations)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/thegreatsantiny/the-dictator.git
cd the-dictator
```

2. Run the setup script:
```bash
bash setup.sh
```

3. Set your Groq API key:
```bash
export GROQ_API_KEY='your-api-key-here'
# Add to ~/.bashrc for persistence
```

4. Configure your desktop environment to run `bash run.sh` on your preferred hotkey (e.g., Alt+Z)

5. Start the service:
```bash
systemctl --user enable --now voice-dictation
```

## Usage

1. Press your configured hotkey (e.g., Alt+Z) to start recording
2. Speak your text
3. Press the hotkey again to stop
4. The transcribed and cleaned text will be typed automatically into the focused application

## Configuration

Edit `config.json` to customize:

- `hotkey` - Toggle hotkey (default: alt+space)
- `whisper_model` - Whisper model to use
- `llm_model` - LLM model for cleanup
- `llm_cleanup` - Enable/disable LLM cleanup
- `clipboard_copy` - Copy text to clipboard
- `language` - Transcription language

## Troubleshooting

### ydotool not working
Ensure ydotoold is running:
```bash
systemctl --user status ydotoold
# If not running:
systemctl --user start ydotoold
```

### Microphone not detected
Check available audio devices:
```bash
pw-record --list-targets
```

Update `voice-dictation.py` with the correct device index (line ~163).

## License

MIT
