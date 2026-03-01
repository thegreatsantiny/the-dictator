#!/bin/bash

echo "=== Voice Dictation Setup ==="

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y pipewire pipewire-utils alsa-utils ffmpeg wl-clipboard ydotool

echo "Setting up udev rules for ydotool..."
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-ydotool.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Creating systemd user service for ydotool..."
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
systemctl --user daemon-reload
systemctl --user enable --now ydotoold

echo "Adding user to input group (requires logout/login)..."
sudo usermod -aG input $USER

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Set your Groq API key:"
echo "   export GROQ_API_KEY='your-api-key-here'"
echo "   (Add to ~/.bashrc for persistence)"
echo ""
echo "2. Log out and log back in (for input group)"
echo ""
echo "3. Test microphone:"
echo "   pw-record --list-targets"
echo ""
echo "4. Run the app:"
echo "   bash run.sh"
