"""
Group Management Commands for ID Finder Pro Bot
Handles all group-specific functionality including user commands and admin commands.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden
import re
from group_db import GroupDatabase

logger = logging.getLogger(__name__)

# Initialize group database
group_db = GroupDatabase()

class GroupCommandHandler:
    """Handles all group-specific commands and functionality"""
    
    def __init__(self):
        self.group_db = group_db
    
    async def is_user_admin(self, context, chat_id: int, user_id: int) -> bool:
        """Check if user is admin in the group"""
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    
    async def get_user_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Extract user info from username mention or replied message"""
        message = update.message
        
        # Check if replying to a message
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            return target_user.id, target_user.username, target_user.first_name
        
        # Check for username in command arguments
        if context.args and len(context.args) > 0:
            username = context.args[0]
            if username.startswith('@'):
                username = username[1:]
            
            try:
                # Try to get user info by username
                chat_member = await context.bot.get_chat_member(message.chat_id, f"@{username}")
                user = chat_member.user
                return user.id, user.username, user.first_name
            except Exception as e:
                logger.error(f"Error getting user by username {username}: {e}")
                return None, None, None
        
        return None, None, None
    
    def parse_time_duration(self, time_str: str) -> timedelta:
        """Parse time duration string like '10m', '2h', '1d' into timedelta"""
        if not time_str:
            return timedelta(hours=1)  # Default 1 hour
        
        time_str = time_str.lower().strip()
        
        # Extract number and unit
        match = re.match(r'^(\d+)([mhd])$', time_str)
        if not match:
            return timedelta(hours=1)  # Default if invalid format
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
        elif unit == 'd':
            return timedelta(days=amount)
        else:
            return timedelta(hours=1)

# Initialize handler instance
group_handler = GroupCommandHandler()

# User Commands (Available to Everyone in Group)

async def group_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the Telegram ID of the user who sent the command"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    user = update.effective_user
    text = (
        f"👤 <b>Your Telegram ID</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Name:</b> {user.first_name}"
    )
    
    if user.last_name:
        text += f" {user.last_name}"
    
    if user.username:
        text += f"\n📎 <b>Username:</b> @{user.username}"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def group_ids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the current group's Telegram ID"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    chat = update.effective_chat
    text = (
        f"👥 <b>Group Information</b>\n\n"
        f"🆔 <b>Group ID:</b> <code>{chat.id}</code>\n"
        f"📝 <b>Title:</b> {chat.title}"
    )
    
    if chat.username:
        text += f"\n📎 <b>Username:</b> @{chat.username}"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def whois_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the Telegram ID and basic info of the mentioned/replied user"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    user_id, username, first_name = await group_handler.get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/whois @username</code> or reply to a message with <code>/whois</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        # Get full user info
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        user = chat_member.user
        
        text = (
            f"👤 <b>User Information</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"👤 <b>Name:</b> {user.first_name}"
        )
        
        if user.last_name:
            text += f" {user.last_name}"
        
        if user.username:
            text += f"\n📎 <b>Username:</b> @{user.username}"
        
        # Add group-specific info
        status_emoji = {
            'creator': '👑',
            'administrator': '🛡️',
            'member': '👤',
            'restricted': '🚫',
            'left': '🚪',
            'kicked': '❌'
        }
        
        status = chat_member.status
        text += f"\n🏷️ <b>Status:</b> {status_emoji.get(status, '❓')} {status.title()}"
        
        if user.is_bot:
            text += f"\n🤖 <b>Type:</b> Bot"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in whois command: {e}")
        await update.message.reply_text(
            "❌ Could not retrieve user information. Make sure the user is in this group.",
            parse_mode='HTML'
        )

async def mentionid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Returns a clickable mention of the replied/mentioned user using their Telegram ID"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    user_id, username, first_name = await group_handler.get_user_from_message(update, context)
    
    if not user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/mentionid @username</code> or reply to a message with <code>/mentionid</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        # Get user info to create proper mention
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        user = chat_member.user
        
        # Create clickable mention using user ID
        mention_text = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        
        await update.message.reply_text(
            f"👤 Clickable mention: {mention_text}\n"
            f"🆔 User ID: <code>{user.id}</code>",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in mentionid command: {e}")
        await update.message.reply_text(
            "❌ Could not create mention. Make sure the user is in this group.",
            parse_mode='HTML'
        )

async def group_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows group-related commands, adapted to user or admin role"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if user is admin
    is_admin = await group_handler.is_user_admin(context, chat_id, user_id)
    
    # Basic user commands
    help_text = (
        "📚 <b>ID Finder Pro Bot - Group Commands</b>\n\n"
        "👤 <b>User Commands:</b>\n"
        "• <code>/id</code> - Show your Telegram ID\n"
        "• <code>/ids</code> - Show this group's ID\n"
        "• <code>/whois @username</code> - Get user info\n"
        "• <code>/mentionid @username</code> - Create clickable mention\n"
        "• <code>/help</code> - Show this help message\n\n"
        "💡 <b>Tip:</b> Most commands work with replies too!"
    )
    
    # Add admin commands if user is admin
    if is_admin:
        help_text += (
            "\n\n🛡️ <b>Admin Commands:</b>\n"
            "• <code>/warn @user [reason]</code> - Warn a user\n"
            "• <code>/warnings @user</code> - Check user warnings\n"
            "• <code>/resetwarn @user</code> - Reset user warnings\n"
            "• <code>/mute @user [time]</code> - Mute user (10m, 2h, 1d)\n"
            "• <code>/unmute @user</code> - Unmute user\n"
            "• <code>/kick @user</code> - Kick user from group\n"
            "• <code>/ban @user</code> - Ban user from group\n"
            "• <code>/unban @user</code> - Unban user\n"
            "• <code>/pin</code> - Pin replied message\n"
            "• <code>/groupinfo</code> - Show group statistics\n"
            "• <code>/listadmins</code> - List all group admins"
        )
    
    await update.message.reply_text(help_text, parse_mode='HTML')

# Admin Commands (Only Usable by Group Admins)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Issues a warning to the user, with optional reason"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/warn @username [reason]</code> or reply to a message with <code>/warn [reason]</code>",
            parse_mode='HTML'
        )
        return

    # Don't allow warning admins
    if await group_handler.is_user_admin(context, chat_id, target_user_id):
        await update.message.reply_text("❌ Cannot warn group administrators.")
        return

    # Get reason from command arguments (skip username if provided)
    reason = "No reason provided"
    if context.args:
        if update.message.reply_to_message:
            # If replying, all args are reason
            reason = " ".join(context.args)
        else:
            # If mentioning, skip first arg (username) and use rest as reason
            if len(context.args) > 1:
                reason = " ".join(context.args[1:])

    # Add warning to database
    warning_count = group_handler.group_db.add_warning(chat_id, target_user_id, reason, user_id)

    # Create mention for target user
    target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

    await update.message.reply_text(
        f"⚠️ <b>Warning Issued</b>\n\n"
        f"👤 <b>User:</b> {target_mention}\n"
        f"📝 <b>Reason:</b> {reason}\n"
        f"📊 <b>Total Warnings:</b> {warning_count}/3\n\n"
        f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
        parse_mode='HTML'
    )

    # Check if user reached warning limit
    if warning_count >= 3:
        await update.message.reply_text(
            f"🚨 <b>Warning Limit Reached!</b>\n\n"
            f"{target_mention} has reached the maximum warning limit (3/3).\n"
            f"Consider taking further action.",
            parse_mode='HTML'
        )

async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows how many warnings the user has received"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/warnings @username</code> or reply to a message with <code>/warnings</code>",
            parse_mode='HTML'
        )
        return

    warnings = group_handler.group_db.get_warnings(chat_id, target_user_id)
    warning_count = len(warnings)

    target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

    if warning_count == 0:
        await update.message.reply_text(
            f"✅ <b>No Warnings</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"📊 <b>Warnings:</b> 0/3\n\n"
            f"This user has a clean record! 🎉",
            parse_mode='HTML'
        )
        return

    # Build warnings list
    warnings_text = f"⚠️ <b>Warning History</b>\n\n👤 <b>User:</b> {target_mention}\n📊 <b>Total:</b> {warning_count}/3\n\n"

    for i, warning in enumerate(warnings[-5:], 1):  # Show last 5 warnings
        date = datetime.fromisoformat(warning['date']).strftime('%Y-%m-%d %H:%M')
        warnings_text += f"<b>{i}.</b> {warning['reason']}\n   📅 {date}\n\n"

    if len(warnings) > 5:
        warnings_text += f"... and {len(warnings) - 5} more warnings"

    await update.message.reply_text(warnings_text, parse_mode='HTML')

async def resetwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets warning count for the mentioned/replied user"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/resetwarn @username</code> or reply to a message with <code>/resetwarn</code>",
            parse_mode='HTML'
        )
        return

    old_count = group_handler.group_db.get_warning_count(chat_id, target_user_id)
    group_handler.group_db.reset_warnings(chat_id, target_user_id)

    target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

    await update.message.reply_text(
        f"🔄 <b>Warnings Reset</b>\n\n"
        f"👤 <b>User:</b> {target_mention}\n"
        f"📊 <b>Previous Warnings:</b> {old_count}\n"
        f"📊 <b>Current Warnings:</b> 0\n\n"
        f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
        parse_mode='HTML'
    )

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mutes the user for a specified duration"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/mute @username [time]</code> or reply to a message with <code>/mute [time]</code>\n"
            "Time examples: 10m, 2h, 1d",
            parse_mode='HTML'
        )
        return

    # Don't allow muting admins
    if await group_handler.is_user_admin(context, chat_id, target_user_id):
        await update.message.reply_text("❌ Cannot mute group administrators.")
        return

    # Parse duration from arguments
    duration_str = "1h"  # Default 1 hour
    if context.args:
        if update.message.reply_to_message:
            # If replying, first arg is duration
            if len(context.args) > 0:
                duration_str = context.args[0]
        else:
            # If mentioning, second arg is duration
            if len(context.args) > 1:
                duration_str = context.args[1]

    duration = group_handler.parse_time_duration(duration_str)

    try:
        # Restrict user permissions
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user_id,
            permissions={
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False
            },
            until_date=datetime.now() + duration
        )

        # Add to database
        group_handler.group_db.add_mute(chat_id, target_user_id, duration, f"Muted for {duration_str}", user_id)

        target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

        await update.message.reply_text(
            f"🔇 <b>User Muted</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"⏰ <b>Duration:</b> {duration_str}\n"
            f"📅 <b>Until:</b> {(datetime.now() + duration).strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to mute user: {e}")
    except Exception as e:
        logger.error(f"Error in mute command: {e}")
        await update.message.reply_text("❌ An error occurred while muting the user.")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmutes a previously muted user"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/unmute @username</code> or reply to a message with <code>/unmute</code>",
            parse_mode='HTML'
        )
        return

    try:
        # Restore user permissions
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user_id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False
            }
        )

        # Remove from database
        group_handler.group_db.remove_mute(chat_id, target_user_id)

        target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

        await update.message.reply_text(
            f"🔊 <b>User Unmuted</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"✅ <b>Status:</b> Can now send messages\n\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to unmute user: {e}")
    except Exception as e:
        logger.error(f"Error in unmute command: {e}")
        await update.message.reply_text("❌ An error occurred while unmuting the user.")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kicks the user from the group"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/kick @username</code> or reply to a message with <code>/kick</code>",
            parse_mode='HTML'
        )
        return

    # Don't allow kicking admins
    if await group_handler.is_user_admin(context, chat_id, target_user_id):
        await update.message.reply_text("❌ Cannot kick group administrators.")
        return

    try:
        # Kick user (ban then unban to allow rejoining)
        await context.bot.ban_chat_member(chat_id, target_user_id)
        await context.bot.unban_chat_member(chat_id, target_user_id)

        target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

        await update.message.reply_text(
            f"👢 <b>User Kicked</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"✅ <b>Status:</b> Removed from group (can rejoin)\n\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to kick user: {e}")
    except Exception as e:
        logger.error(f"Error in kick command: {e}")
        await update.message.reply_text("❌ An error occurred while kicking the user.")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bans the user from the group"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/ban @username</code> or reply to a message with <code>/ban</code>",
            parse_mode='HTML'
        )
        return

    # Don't allow banning admins
    if await group_handler.is_user_admin(context, chat_id, target_user_id):
        await update.message.reply_text("❌ Cannot ban group administrators.")
        return

    try:
        # Ban user permanently
        await context.bot.ban_chat_member(chat_id, target_user_id)

        target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

        await update.message.reply_text(
            f"🚫 <b>User Banned</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"❌ <b>Status:</b> Permanently banned from group\n\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to ban user: {e}")
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await update.message.reply_text("❌ An error occurred while banning the user.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unbans a previously banned user"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    target_user_id, target_username, target_first_name = await group_handler.get_user_from_message(update, context)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Please reply to a user's message or mention a username.\n"
            "Usage: <code>/unban @username</code> or reply to a message with <code>/unban</code>",
            parse_mode='HTML'
        )
        return

    try:
        # Unban user
        await context.bot.unban_chat_member(chat_id, target_user_id)

        target_mention = f'<a href="tg://user?id={target_user_id}">{target_first_name}</a>'

        await update.message.reply_text(
            f"✅ <b>User Unbanned</b>\n\n"
            f"👤 <b>User:</b> {target_mention}\n"
            f"🔓 <b>Status:</b> Can now rejoin the group\n\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to unban user: {e}")
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await update.message.reply_text("❌ An error occurred while unbanning the user.")

async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pins the replied message"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Please reply to a message to pin it.\n"
            "Usage: Reply to any message and send <code>/pin</code>",
            parse_mode='HTML'
        )
        return

    try:
        # Pin the replied message
        await context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=update.message.reply_to_message.message_id,
            disable_notification=False
        )

        await update.message.reply_text(
            f"📌 <b>Message Pinned</b>\n\n"
            f"✅ The replied message has been pinned to the group.\n"
            f"🛡️ <b>Admin:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )

    except BadRequest as e:
        await update.message.reply_text(f"❌ Failed to pin message: {e}")
    except Exception as e:
        logger.error(f"Error in pin command: {e}")
        await update.message.reply_text("❌ An error occurred while pinning the message.")

async def groupinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows group stats: title, ID, total members, admins count, etc."""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    try:
        chat = await context.bot.get_chat(chat_id)
        member_count = await context.bot.get_chat_member_count(chat_id)

        # Get admin count
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_count = len(admins)

        # Get moderation stats
        mod_stats = group_handler.group_db.get_group_stats(chat_id)

        info_text = (
            f"📊 <b>Group Information</b>\n\n"
            f"📝 <b>Title:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
        )

        if chat.username:
            info_text += f"📎 <b>Username:</b> @{chat.username}\n"

        if chat.description:
            description = chat.description[:100] + "..." if len(chat.description) > 100 else chat.description
            info_text += f"📄 <b>Description:</b> {description}\n"

        info_text += (
            f"\n👥 <b>Members:</b> {member_count:,}\n"
            f"🛡️ <b>Administrators:</b> {admin_count}\n"
            f"📅 <b>Type:</b> {'Supergroup' if chat.type == 'supergroup' else 'Group'}\n"
        )

        # Add moderation stats
        info_text += (
            f"\n📈 <b>Moderation Stats:</b>\n"
            f"⚠️ <b>Total Warnings:</b> {mod_stats['total_warnings']}\n"
            f"👤 <b>Users with Warnings:</b> {mod_stats['users_with_warnings']}\n"
            f"🔇 <b>Active Mutes:</b> {mod_stats['active_mutes']}\n"
            f"📊 <b>Total Moderated Users:</b> {mod_stats['total_users_moderated']}"
        )

        await update.message.reply_text(info_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in groupinfo command: {e}")
        await update.message.reply_text("❌ An error occurred while getting group information.")

async def listadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all current admins with usernames and IDs"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if user is admin
    if not await group_handler.is_user_admin(context, chat_id, user_id):
        await update.message.reply_text("❌ This command is only available to group administrators.")
        return

    try:
        admins = await context.bot.get_chat_administrators(chat_id)

        admin_text = f"🛡️ <b>Group Administrators</b>\n\n"

        creators = []
        administrators = []

        for admin in admins:
            user = admin.user

            # Create user info string
            user_info = f"👤 {user.first_name}"
            if user.last_name:
                user_info += f" {user.last_name}"

            if user.username:
                user_info += f" (@{user.username})"

            user_info += f"\n   🆔 <code>{user.id}</code>"

            if user.is_bot:
                user_info += " 🤖"

            if admin.status == 'creator':
                creators.append(user_info)
            else:
                administrators.append(user_info)

        # Add creators first
        if creators:
            admin_text += "👑 <b>Group Creator:</b>\n"
            for creator in creators:
                admin_text += f"{creator}\n\n"

        # Add administrators
        if administrators:
            admin_text += f"🛡️ <b>Administrators ({len(administrators)}):</b>\n"
            for i, admin in enumerate(administrators, 1):
                admin_text += f"<b>{i}.</b> {admin}\n\n"

        admin_text += f"📊 <b>Total:</b> {len(admins)} administrators"

        await update.message.reply_text(admin_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in listadmins command: {e}")
        await update.message.reply_text("❌ An error occurred while getting admin list.")
