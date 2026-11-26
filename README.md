# The Dictator - Voice Dictation for Linux

A hands-free voice dictation system for Linux that transcribes your voice and types it directly into any application.

## Features

- **Voice to Text** - Uses Groq's Whisper API for fast, accurate transcription
- **AI Cleanup** - Uses an LLM to clean up transcription (fixes punctuation, capitalization, filler words)
- **Auto-Typing** - Automatically types the transcribed text into the focused application using ydotool
- **System Notifications** - Shows status notifications during recording, processing, and completion
- **Systemd Service** - Runs as a background service, auto-starts on login

## Requirements

- Linux with PipeWire and a desktop environment that supports custom keybindings (e.g. GNOME)
- Groq API key (free at groq.com)
- ydotool, wl-clipboard
- Python 3 with `venv` support

## Setup

1. Clone the repository and enter it:
   ```bash
   git clone https://github.com/thegreatsantiny/the-dictator.git
   cd the-dictator
   ```

2. Run the setup script. It installs system packages, creates a Python virtual environment in `venv/`, installs the Python dependencies, and installs both `voice-dictation.service` and `ydotoold.service`:
   ```bash
   bash setup.sh
   ```

3. Add your Groq API key to `.env`:
   ```bash
   echo "GROQ_API_KEY='your-api-key-here'" > .env
   chmod 600 .env
   ```

4. Log out and back in so the `input` group change takes effect.

5. Add a custom keybinding in your desktop environment (GNOME: Settings > Keyboard > Custom Shortcuts):
   - **Name:** Voice Dictation AI
   - **Command:** `touch /tmp/voice-dictation.toggle`
   - **Shortcut:** `Alt+Z`

6. Verify the daemon is running:
   ```bash
   systemctl --user status voice-dictation.service
   ```

## Usage

1. Press `Alt+Z` to start recording; a "Recording..." notification appears.
2. Speak your text.
3. Press `Alt+Z` again to stop; the text is transcribed, cleaned up, and typed into the focused application.

## How the hotkey works

The keybinding does **not** launch the app. It simply creates `/tmp/voice-dictation.toggle`. The background daemon polls for that file every 0.1 seconds and toggles recording, so the service must be running for `Alt+Z` to do anything. `run.sh` is an alternative launcher that starts the daemon when it isn't running and toggles it when it is.

## Configuration

`config.json` is local and gitignored. Copy `config.example.json` to `config.json` to get started, then edit as needed:

- `audio_device` - `"default"`, `"pipewire"`, a substring of a device name, or a numeric device index
- `whisper_model` - Whisper model to use
- `llm_model` - LLM model used for cleanup
- `llm_cleanup` - Enable/disable LLM cleanup
- `clipboard_copy` - Copy the result to the clipboard
- `language` - Transcription language
- `corrections_file` - Path to a word-replacement dictionary

The hotkey itself is configured in your desktop environment, not in `config.json`.

## Troubleshooting

### Nothing happens when I press Alt+Z

Check that the daemon is running and the keybinding command is exactly `touch /tmp/voice-dictation.toggle`:
```bash
systemctl --user status voice-dictation.service
tail -f /tmp/voice-dictation.log
```

If you upgraded your system Python (e.g. 3.12 to 3.14), pip-installed packages stay in the old Python's user site directory and the daemon will crash-loop with `ModuleNotFoundError`. Re-run `bash setup.sh` to rebuild the virtual environment for the current interpreter.

### ydotool not working

Ensure ydotoold is running:
```bash
systemctl --user status ydotoold.service
# If not running:
systemctl --user start ydotoold.service
```

### Microphone not detected

List available input devices:
```bash
pw-record --list-targets
```

Then set the matching `audio_device` value in `config.json` (name substring or numeric index).

## License

MIT
