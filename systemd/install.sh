#!/bin/bash

# Systemd installation script for GEE services

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Installing GEE systemd services..."

# Create gee user if it doesn't exist
if ! id -u gee > /dev/null 2>&1; then
    echo "Creating gee user..."
    useradd -r -s /bin/false -d /opt/gee -m gee
fi

# Create log directory
mkdir -p /var/log/gee
chown gee:gee /var/log/gee

# Copy service files
cp gee-forge.service /etc/systemd/system/
cp gee-praxis.service /etc/systemd/system/

# Create target for both services
cat > /etc/systemd/system/gee.target << EOF
[Unit]
Description=GEE System - Rules Engine Platform
Requires=gee-forge.service gee-praxis.service
After=gee-forge.service gee-praxis.service

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo "GEE services installed successfully!"
echo ""
echo "Usage:"
echo "  Start all:    sudo systemctl start gee.target"
echo "  Stop all:     sudo systemctl stop gee.target"
echo "  Status:       sudo systemctl status gee-*"
echo "  Enable boot:  sudo systemctl enable gee.target"
echo ""
echo "Individual services:"
echo "  Forge:   sudo systemctl {start|stop|restart|status} gee-forge"
echo "  Praxis:  sudo systemctl {start|stop|restart|status} gee-praxis"
echo ""
echo "View logs:"
echo "  Forge:   sudo journalctl -u gee-forge -f"
echo "  Praxis:  sudo journalctl -u gee-praxis -f"