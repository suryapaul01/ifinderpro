# VPS Troubleshooting Guide - ID Finder Bot

## 🚨 Common Error: 'UserShared' object has no attribute 'user_ids'

This error occurs due to version compatibility issues between different versions of python-telegram-bot.

### Quick Fix Steps:

1. **Check your python-telegram-bot version:**
   ```bash
   cd ~/idFinder_Bot
   source venv/bin/activate
   pip show python-telegram-bot
   ```

2. **Update to the latest version:**
   ```bash
   pip install --upgrade python-telegram-bot[asyncio]
   ```

3. **If still having issues, try specific version:**
   ```bash
   pip install python-telegram-bot[asyncio]==20.7
   ```

4. **Run the debug script:**
   ```bash
   python3 debug_version.py
   ```

5. **Test basic functionality:**
   ```bash
   python3 test_bot.py
   ```

### Detailed Troubleshooting:

#### Step 1: Check System Environment

```bash
# Check Python version (should be 3.8+)
python3 --version

# Check pip version
pip --version

# Check virtual environment
which python3
which pip
```

#### Step 2: Clean Installation

If you're still having issues, try a clean installation:

```bash
# Stop the bot service
sudo systemctl stop idfinder-bot.service

# Remove old virtual environment
cd ~/idFinder_Bot
rm -rf venv

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install specific working version
pip install python-telegram-bot[asyncio]==20.7
pip install aiosqlite python-dotenv requests pytonlib

# Test the installation
python3 debug_version.py
```

#### Step 3: Check Bot Configuration

```bash
# Verify config.py exists and is correct
cat config.py

# Test bot token
python3 -c "
from config import BOT_TOKEN
print('Bot token length:', len(BOT_TOKEN))
print('Bot token starts with:', BOT_TOKEN[:10] + '...')
"
```

#### Step 4: Test Network Connectivity

```bash
# Test Telegram API connectivity
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getMe" | python3 -m json.tool

# Replace $BOT_TOKEN with your actual token, or test manually:
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

#### Step 5: Check Logs and Debug

```bash
# Check system logs
sudo journalctl -u idfinder-bot.service --no-pager -n 50

# Run bot manually to see errors
cd ~/idFinder_Bot
source venv/bin/activate
python3 bot.py
```

## 🔧 Specific Error Solutions

### Error: "per_message=False"

This warning can be ignored, but if you want to fix it:

```python
# In bot.py, find the ConversationHandler and add:
per_message=False,
per_chat=True,
per_user=True,
```

### Error: Module Import Issues

```bash
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

### Error: Permission Denied

```bash
# Fix file permissions
sudo chown -R $USER:$USER ~/idFinder_Bot
chmod +x ~/idFinder_Bot/*.py
```

### Error: Port/Network Issues

```bash
# Check if any process is blocking
sudo netstat -tulpn | grep :443
sudo netstat -tulpn | grep :80

# Check firewall
sudo ufw status
```

## 🐛 Advanced Debugging

### Enable Debug Logging

Edit your `bot.py` and change the logging level:

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Change from INFO to DEBUG
)
```

### Create Debug Service

Create a debug version of the systemd service:

```bash
sudo cp /etc/systemd/system/idfinder-bot.service /etc/systemd/system/idfinder-bot-debug.service
```

Edit the debug service:
```bash
sudo nano /etc/systemd/system/idfinder-bot-debug.service
```

Change the ExecStart line to:
```ini
ExecStart=/home/botuser/idFinder_Bot/venv/bin/python -u bot.py
Environment=PYTHONUNBUFFERED=1
```

### Monitor Resource Usage

```bash
# Check memory usage
free -h

# Check disk space
df -h

# Monitor bot process
top -p $(pgrep -f "python.*bot.py")
```

## 📋 Version Compatibility Matrix

| python-telegram-bot | Python | Status | Notes |
|-------------------|--------|--------|-------|
| 20.7 | 3.8+ | ✅ Recommended | Latest stable |
| 20.6 | 3.8+ | ✅ Good | Stable |
| 20.0-20.5 | 3.8+ | ⚠️ May have issues | UserShared compatibility |
| 13.x | 3.7+ | ❌ Not supported | Too old |

## 🚀 Quick Recovery Commands

```bash
# Complete bot restart
sudo systemctl stop idfinder-bot.service
sudo systemctl start idfinder-bot.service
sudo systemctl status idfinder-bot.service

# View recent logs
sudo journalctl -u idfinder-bot.service -f --since "5 minutes ago"

# Emergency manual run
cd ~/idFinder_Bot
source venv/bin/activate
python3 bot.py

# Update and restart
cd ~/idFinder_Bot
git pull
sudo systemctl restart idfinder-bot.service
```

## 📞 Getting Help

If you're still having issues:

1. **Run the debug script and share output:**
   ```bash
   python3 debug_version.py > debug_output.txt 2>&1
   cat debug_output.txt
   ```

2. **Share the exact error message:**
   ```bash
   sudo journalctl -u idfinder-bot.service --no-pager -n 20
   ```

3. **Check your system info:**
   ```bash
   uname -a
   python3 --version
   pip show python-telegram-bot
   ```

## 🎯 Prevention Tips

1. **Always use virtual environments**
2. **Pin dependency versions in requirements.txt**
3. **Test after updates**
4. **Monitor logs regularly**
5. **Keep backups of working configurations**

---

**Remember:** The most common issue is version compatibility. Always try updating python-telegram-bot first!
