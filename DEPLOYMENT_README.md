# ID Finder Bot - Quick Deployment Guide

## 🚀 Quick Start (Ubuntu VPS)

### Option 1: Automated Installation

1. **Upload your bot files to the VPS:**
   ```bash
   scp -r idFinder_Bot/ user@your-vps-ip:~/
   ```

2. **SSH into your VPS:**
   ```bash
   ssh user@your-vps-ip
   ```

3. **Run the installation script:**
   ```bash
   cd idFinder_Bot
   chmod +x install_vps.sh
   ./install_vps.sh
   ```

4. **Configure your bot token:**
   ```bash
   nano config.py
   ```
   Add your bot token and admin IDs.

5. **Restart the service:**
   ```bash
   sudo systemctl restart idfinder-bot.service
   ```

### Option 2: Manual Installation

Follow the detailed guide in `VPS_DEPLOYMENT_GUIDE.md`

## 🔧 Essential Commands

```bash
# Check bot status
sudo systemctl status idfinder-bot.service

# View live logs
sudo journalctl -u idfinder-bot.service -f

# Restart bot
sudo systemctl restart idfinder-bot.service

# Update bot code
cd ~/idFinder_Bot
git pull
sudo systemctl restart idfinder-bot.service
```

## 🐛 Troubleshooting

### Bot not responding to forwarded messages?

1. **Check logs:**
   ```bash
   sudo journalctl -u idfinder-bot.service -f
   ```

2. **Ensure latest python-telegram-bot:**
   ```bash
   cd ~/idFinder_Bot
   source venv/bin/activate
   pip install --upgrade python-telegram-bot[asyncio]
   sudo systemctl restart idfinder-bot.service
   ```

### Username command not working?

1. **Test network connectivity:**
   ```bash
   curl -I https://api.telegram.org
   ```

2. **Check bot permissions and logs**

### Service won't start?

1. **Check service logs:**
   ```bash
   sudo journalctl -u idfinder-bot.service --no-pager
   ```

2. **Verify config.py:**
   ```bash
   cd ~/idFinder_Bot
   python3 -c "import config; print('Config loaded successfully')"
   ```

## 📋 System Requirements

- **OS:** Ubuntu 18.04+ (or similar Linux distribution)
- **Python:** 3.8+
- **RAM:** 512MB minimum (1GB recommended)
- **Storage:** 1GB free space
- **Network:** Stable internet connection

## 🔒 Security Notes

- The bot runs as a non-root user
- Firewall configuration is recommended
- Regular system updates are important
- Keep your bot token secure

## 📞 Support

If you encounter issues:

1. Check the logs first: `sudo journalctl -u idfinder-bot.service -f`
2. Verify your configuration
3. Ensure all dependencies are installed
4. Check network connectivity to Telegram API

## 🎯 Features Verified on VPS

✅ **Working Features:**
- /start command
- /id command  
- /username command (with improved error handling)
- /add command (simplified single button)
- Forwarded message processing (with fallback support)
- Admin commands
- Inline queries

✅ **Fixed Issues:**
- /add command now shows single button and directly adds bot
- /username command has better error messages and debugging
- Forwarded messages work with both new and legacy Bot API versions
- Comprehensive logging for troubleshooting

## 📈 Monitoring

Monitor your bot with:

```bash
# System resources
htop

# Bot logs
sudo journalctl -u idfinder-bot.service -f

# Service status
sudo systemctl status idfinder-bot.service

# Disk usage
df -h
```

---

**Happy Botting! 🤖**
