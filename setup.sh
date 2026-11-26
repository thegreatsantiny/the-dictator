#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Voice Dictation Setup ==="

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y pipewire pipewire-utils alsa-utils ffmpeg wl-clipboard ydotool python3-pip python3-venv

echo "Setting up udev rules for ydotool..."
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-ydotool.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Creating Python virtual environment..."
rm -rf venv
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "Creating systemd user services..."
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/ydotoold.service << 'EOF'
[Unit]
Description=ydotool daemon

[Service]
ExecStart=/usr/bin/ydotoold
Restart=on-failure

[Install]
WantedBy=default.target
EOF

cat > ~/.config/systemd/user/voice-dictation.service << EOF
[Unit]
Description=Voice Dictation AI
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/voice-dictation.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ydotoold

if [ -f .env ]; then
    systemctl --user enable --now voice-dictation.service
else
    systemctl --user enable voice-dictation.service
    echo "WARNING: .env not found; start the service after adding your API key."
fi

echo "Adding user to input group (requires logout/login)..."
sudo usermod -aG input "$USER"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Put your Groq API key in $SCRIPT_DIR/.env:"
echo "   GROQ_API_KEY='your-api-key-here'"
echo "   chmod 600 $SCRIPT_DIR/.env"
echo ""
echo "2. Log out and log back in (for the input group)."
echo ""
echo "3. Add a GNOME custom shortcut (Settings > Keyboard > Custom Shortcuts):"
echo "   Name:     Voice Dictation AI"
echo "   Command:  touch /tmp/voice-dictation.toggle"
echo "   Shortcut: Alt+Z"
echo ""
echo "4. Test the microphone:"
echo "   pw-record --list-targets"
echo ""
echo "5. Check the service:"
echo "   systemctl --user status voice-dictation.service"
