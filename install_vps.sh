#!/bin/bash

# ID Finder Bot - VPS Installation Script for Ubuntu
# This script automates the deployment process

set -e

echo "🚀 ID Finder Bot VPS Installation Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons."
   print_status "Please run as a regular user with sudo privileges."
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    screen \
    tmux \
    htop \
    nano

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_error "Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

print_status "Python version check passed: $python_version"

# Create project directory
PROJECT_DIR="$HOME/idFinder_Bot"
if [ -d "$PROJECT_DIR" ]; then
    print_warning "Directory $PROJECT_DIR already exists."
    read -p "Do you want to remove it and start fresh? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$PROJECT_DIR"
        print_status "Removed existing directory."
    else
        print_status "Using existing directory."
    fi
fi

# Clone or use existing repository
if [ ! -d "$PROJECT_DIR" ]; then
    print_status "Please ensure your bot files are in $PROJECT_DIR"
    print_status "You can either:"
    echo "  1. Clone from git: git clone <your-repo-url> $PROJECT_DIR"
    echo "  2. Copy files manually to $PROJECT_DIR"
    echo ""
    read -p "Press Enter when your bot files are ready in $PROJECT_DIR..."
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Create virtual environment
print_status "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Install additional packages that might be needed on VPS
    print_status "Installing additional VPS-specific packages..."
    pip install --upgrade python-telegram-bot[asyncio]
    pip install aiofiles psutil certifi
else
    print_error "requirements.txt not found!"
    print_status "Installing basic dependencies..."
    pip install python-telegram-bot[asyncio] aiosqlite python-dotenv requests pytonlib
fi

# Check for config file
if [ ! -f "config.py" ]; then
    print_warning "config.py not found!"
    if [ -f "config.py.example" ]; then
        cp config.py.example config.py
        print_status "Created config.py from example."
    else
        print_status "Creating basic config.py..."
        cat > config.py << 'EOF'
# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = ["YOUR_TELEGRAM_USER_ID"]
TON_WALLET = "YOUR_TON_WALLET_ADDRESS"  # Optional
EOF
    fi
    
    print_warning "Please edit config.py with your bot token and settings:"
    echo "  nano config.py"
    echo ""
    read -p "Press Enter after you've configured config.py..."
fi

# Test bot
print_status "Testing bot configuration..."
timeout 10s python3 bot.py || {
    print_warning "Bot test failed or timed out. This might be normal if the bot is waiting for updates."
    print_status "You can test manually later with: python3 bot.py"
}

# Create systemd service
print_status "Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/idfinder-bot.service"

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=ID Finder Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
print_status "Enabling and starting systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable idfinder-bot.service
sudo systemctl start idfinder-bot.service

# Check service status
sleep 3
if sudo systemctl is-active --quiet idfinder-bot.service; then
    print_status "✅ Bot service is running successfully!"
else
    print_error "❌ Bot service failed to start."
    print_status "Check logs with: sudo journalctl -u idfinder-bot.service -f"
fi

# Setup log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/idfinder-bot > /dev/null << 'EOF'
/home/*/idFinder_Bot/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Create useful aliases
print_status "Creating useful aliases..."
cat >> ~/.bashrc << 'EOF'

# ID Finder Bot aliases
alias bot-status='sudo systemctl status idfinder-bot.service'
alias bot-logs='sudo journalctl -u idfinder-bot.service -f'
alias bot-restart='sudo systemctl restart idfinder-bot.service'
alias bot-stop='sudo systemctl stop idfinder-bot.service'
alias bot-start='sudo systemctl start idfinder-bot.service'
alias bot-update='cd ~/idFinder_Bot && git pull && sudo systemctl restart idfinder-bot.service'
EOF

print_status "🎉 Installation completed successfully!"
echo ""
echo "📋 Quick Commands:"
echo "  • Check bot status: sudo systemctl status idfinder-bot.service"
echo "  • View bot logs: sudo journalctl -u idfinder-bot.service -f"
echo "  • Restart bot: sudo systemctl restart idfinder-bot.service"
echo "  • Stop bot: sudo systemctl stop idfinder-bot.service"
echo ""
echo "🔧 Configuration:"
echo "  • Bot files: $PROJECT_DIR"
echo "  • Config file: $PROJECT_DIR/config.py"
echo "  • Service file: $SERVICE_FILE"
echo ""
echo "📝 Next steps:"
echo "  1. Verify your bot is working by sending /start to it on Telegram"
echo "  2. Test forwarded message functionality"
echo "  3. Monitor logs for any issues"
echo ""
print_status "Reload your shell to use new aliases: source ~/.bashrc"
