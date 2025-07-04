#!/usr/bin/env python3
"""
Simple test script to verify bot functionality
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple start command for testing"""
    await update.message.reply_text(
        "🤖 Test Bot is working!\n\n"
        "This is a simple test to verify the bot can:\n"
        "✅ Receive messages\n"
        "✅ Send responses\n"
        "✅ Handle commands\n\n"
        "If you see this message, the basic bot functionality is working!"
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to verify bot functionality"""
    user = update.effective_user
    chat = update.effective_chat
    
    text = (
        f"🧪 <b>Bot Test Results</b>\n\n"
        f"👤 <b>User:</b> {user.first_name or 'Unknown'}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💬 <b>Chat Type:</b> {chat.type}\n"
        f"🔗 <b>Chat ID:</b> <code>{chat.id}</code>\n\n"
        f"✅ Bot is receiving and processing messages correctly!"
    )
    
    await update.message.reply_text(text, parse_mode='HTML')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            f"❌ An error occurred: {str(context.error)[:100]}..."
        )

def main():
    """Main function to run the test bot"""
    try:
        # Import config
        from config import BOT_TOKEN
        logger.info("✅ Config imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import config: {e}")
        logger.info("Please ensure config.py exists with BOT_TOKEN defined")
        return
    
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Application created successfully")
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("test", test_command))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("✅ Handlers added successfully")
        logger.info("🚀 Starting test bot...")
        logger.info("Send /start or /test to the bot to verify it's working")
        logger.info("Press Ctrl+C to stop")
        
        # Run the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        logger.info("\n🔧 Troubleshooting steps:")
        logger.info("1. Check your BOT_TOKEN in config.py")
        logger.info("2. Ensure internet connection is working")
        logger.info("3. Verify python-telegram-bot is installed: pip list | grep telegram")
        logger.info("4. Run debug_version.py to check compatibility")

if __name__ == "__main__":
    main()
