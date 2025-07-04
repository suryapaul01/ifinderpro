#!/usr/bin/env python3
"""
Debug script to check python-telegram-bot version and compatibility
"""

import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    logger.info(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error("Python 3.8+ is required!")
        return False
    return True

def check_telegram_bot_version():
    """Check python-telegram-bot version and features"""
    try:
        import telegram
        logger.info(f"python-telegram-bot version: {telegram.__version__}")
        
        # Check for specific classes and attributes
        from telegram import Update
        from telegram.ext import filters
        
        # Check for UserShared and related classes
        try:
            from telegram import UserShared, UsersShared
            logger.info("✅ UserShared and UsersShared classes available")
        except ImportError as e:
            logger.warning(f"⚠️ UserShared/UsersShared classes not available: {e}")
        
        # Check for ChatShared
        try:
            from telegram import ChatShared
            logger.info("✅ ChatShared class available")
        except ImportError as e:
            logger.warning(f"⚠️ ChatShared class not available: {e}")
        
        # Check filters
        try:
            filters.StatusUpdate.USERS_SHARED
            logger.info("✅ USERS_SHARED filter available")
        except AttributeError as e:
            logger.warning(f"⚠️ USERS_SHARED filter not available: {e}")
            
        try:
            filters.StatusUpdate.CHAT_SHARED
            logger.info("✅ CHAT_SHARED filter available")
        except AttributeError as e:
            logger.warning(f"⚠️ CHAT_SHARED filter not available: {e}")
            
        return True
        
    except ImportError as e:
        logger.error(f"❌ python-telegram-bot not installed: {e}")
        return False

def check_dependencies():
    """Check other dependencies"""
    dependencies = [
        'aiosqlite',
        'python-dotenv',
        'requests'
    ]
    
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            logger.info(f"✅ {dep} available")
        except ImportError:
            logger.warning(f"⚠️ {dep} not available")

def test_message_attributes():
    """Test what attributes are available on Message objects"""
    try:
        from telegram import Message, User, Chat
        from telegram.constants import ChatType
        
        # Create a dummy message to check attributes
        logger.info("Available Message attributes related to sharing:")
        
        # List attributes that might be related to sharing
        message_attrs = [attr for attr in dir(Message) if 'shar' in attr.lower()]
        if message_attrs:
            logger.info(f"Message sharing attributes: {message_attrs}")
        else:
            logger.info("No sharing-related attributes found in Message class")
            
        # Check all attributes
        all_attrs = [attr for attr in dir(Message) if not attr.startswith('_')]
        logger.info(f"All Message attributes: {all_attrs}")
        
    except Exception as e:
        logger.error(f"Error checking message attributes: {e}")

def main():
    """Main debug function"""
    logger.info("🔍 Starting python-telegram-bot compatibility check...")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check telegram bot library
    if not check_telegram_bot_version():
        sys.exit(1)
    
    # Check other dependencies
    check_dependencies()
    
    # Test message attributes
    test_message_attributes()
    
    logger.info("✅ Compatibility check completed!")
    
    # Provide recommendations
    logger.info("\n📋 Recommendations:")
    logger.info("1. Ensure you're using python-telegram-bot >= 20.0")
    logger.info("2. If you see warnings above, update with: pip install --upgrade python-telegram-bot[asyncio]")
    logger.info("3. Check the bot logs for specific error messages")

if __name__ == "__main__":
    main()
