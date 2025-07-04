# ID Finder Bot - VPS Deployment Guide for Ubuntu

This guide will help you deploy the ID Finder Bot on an Ubuntu VPS server.

## Prerequisites

- Ubuntu 18.04 or later
- Root or sudo access
- Your bot token from @BotFather

## Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

## Step 2: Install Python and Required System Packages

```bash
# Install Python 3.9+ and pip
sudo apt install python3 python3-pip python3-venv git curl wget -y

# Install additional system dependencies
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y

# Install screen or tmux for running the bot in background
sudo apt install screen tmux -y
```

## Step 3: Create a User for the Bot (Optional but Recommended)

```bash
# Create a new user for the bot
sudo adduser botuser

# Add user to sudo group (if needed)
sudo usermod -aG sudo botuser

# Switch to the bot user
su - botuser
```

## Step 4: Clone and Setup the Bot

```bash
# Clone your bot repository
git clone https://github.com/yourusername/idFinder_Bot.git
cd idFinder_Bot

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

## Step 5: Configure the Bot

```bash
# Copy config template (if you have one)
cp config.py.example config.py

# Edit the configuration file
nano config.py
```

Make sure your `config.py` contains:
```python
BOT_TOKEN = "your_bot_token_here"
ADMIN_IDS = ["your_telegram_user_id"]
TON_WALLET = "your_ton_wallet_address"  # Optional
```

## Step 6: Install Additional Dependencies for VPS

Some features might need additional packages on VPS:

```bash
# Install additional Python packages that might be missing
pip install --upgrade python-telegram-bot[asyncio]
pip install aiofiles
pip install psutil

# If you encounter SSL issues
pip install --upgrade certifi
```

## Step 7: Test the Bot

```bash
# Test run the bot
python bot.py
```

If you see "Bot is ready! Press Ctrl+C to stop." - the bot is working correctly.

## Step 8: Setup Systemd Service (Recommended)

Create a systemd service to run the bot automatically:

```bash
# Create service file
sudo nano /etc/systemd/system/idfinder-bot.service
```

Add the following content:
```ini
[Unit]
Description=ID Finder Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/idFinder_Bot
Environment=PATH=/home/botuser/idFinder_Bot/venv/bin
ExecStart=/home/botuser/idFinder_Bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable the service
sudo systemctl enable idfinder-bot.service

# Start the service
sudo systemctl start idfinder-bot.service

# Check status
sudo systemctl status idfinder-bot.service
```

## Step 9: Setup Firewall (Optional)

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS if needed
sudo ufw allow 80
sudo ufw allow 443
```

## Step 10: Setup Log Rotation

```bash
# Create log rotation config
sudo nano /etc/logrotate.d/idfinder-bot
```

Add:
```
/home/botuser/idFinder_Bot/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
```

## Troubleshooting Common Issues

### 1. Forwarded Messages Not Working

If forwarded messages aren't being processed:

```bash
# Check bot logs
sudo journalctl -u idfinder-bot.service -f

# Ensure python-telegram-bot is latest version
pip install --upgrade python-telegram-bot[asyncio]
```

### 2. Username Resolution Issues

```bash
# Install additional networking tools
sudo apt install dnsutils curl

# Test network connectivity
curl -I https://api.telegram.org
```

### 3. Permission Issues

```bash
# Fix file permissions
chmod +x bot.py
chown -R botuser:botuser /home/botuser/idFinder_Bot
```

### 4. Memory Issues

```bash
# Check memory usage
free -h

# If low on memory, create swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Useful Commands

```bash
# View bot logs
sudo journalctl -u idfinder-bot.service -f

# Restart bot
sudo systemctl restart idfinder-bot.service

# Stop bot
sudo systemctl stop idfinder-bot.service

# Update bot code
cd /home/botuser/idFinder_Bot
git pull
sudo systemctl restart idfinder-bot.service

# Check bot status
sudo systemctl status idfinder-bot.service
```

## Alternative: Running with Screen

If you prefer using screen instead of systemd:

```bash
# Start a screen session
screen -S idbot

# Run the bot
cd idFinder_Bot
source venv/bin/activate
python bot.py

# Detach from screen: Ctrl+A, then D
# Reattach to screen: screen -r idbot
```

## Security Recommendations

1. **Keep system updated**: `sudo apt update && sudo apt upgrade`
2. **Use SSH keys** instead of passwords
3. **Change default SSH port**
4. **Enable fail2ban**: `sudo apt install fail2ban`
5. **Regular backups** of your bot configuration

## Performance Optimization

```bash
# Install htop for monitoring
sudo apt install htop

# Monitor bot performance
htop

# Check disk usage
df -h

# Check bot memory usage
ps aux | grep python
```

This guide should help you successfully deploy your ID Finder Bot on Ubuntu VPS with all features working properly.
