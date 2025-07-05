import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, KeyboardButton, ReplyKeyboardMarkup, LabeledPrice, KeyboardButtonRequestChat, KeyboardButtonRequestUsers, ReplyKeyboardRemove, BotCommand, ChatMember, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler, ConversationHandler, PreCheckoutQueryHandler, ChatMemberHandler)
from config import BOT_TOKEN, ADMIN_IDS, TON_WALLET
from utils import extract_entity_info, format_entity_response, resolve_username_or_link, get_user_chats
from user_db import user_db
import uuid
from datetime import datetime

# Import group commands
from group_commands import (
    group_id_command, group_ids_command, whois_command, mentionid_command,
    group_help_command, help_group_command, help_admin_command, warn_command, warnings_command, resetwarn_command,
    mute_command, unmute_command, kick_command, ban_command, unban_command,
    pin_command, groupinfo_command, listadmins_command
)

# Set logging level to only show important messages
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # Changed from INFO to WARNING to reduce log output
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_ENTITY, SELECTING_CHAT, SELECTING_DONATION_METHOD, SELECTING_STARS_AMOUNT, SELECTING_TON_AMOUNT, WAITING_FOR_USERNAME, WAITING_FOR_MEMBER_USERNAME, NOTIFY_TEXT, NOTIFY_BUTTONS, NOTIFY_CONFIRM = range(10)

# Main keyboard with entity buttons and donate button - always visible
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [
        KeyboardButton(
            text="👤 User",
            request_users=KeyboardButtonRequestUsers(
                request_id=1,
                user_is_bot=False
            )
        ),
        KeyboardButton(
            text="🤖 Bot",
            request_users=KeyboardButtonRequestUsers(
                request_id=2,
                user_is_bot=True
            )
        )
    ],
    [
        KeyboardButton(
            text="👥 Group",
            request_chat=KeyboardButtonRequestChat(
                request_id=3,
                chat_is_channel=False
            )
        ),
        KeyboardButton(
            text="📢 Channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=4,
                chat_is_channel=True
            )
        )
    ],
    [KeyboardButton(text="💰 Donate")]
], resize_keyboard=True)

# Admin keyboard with only group and channel buttons
ADMIN_KEYBOARD = ReplyKeyboardMarkup([
    [
        KeyboardButton(
            text="👥 Group",
            request_chat=KeyboardButtonRequestChat(
                request_id=5,
                chat_is_channel=False,
                chat_is_forum=None,
                chat_has_username=None,
                chat_is_created=True,
                user_administrator_rights={"can_delete_messages": True}
            )
        ),
        KeyboardButton(
            text="📢 Channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=6,
                chat_is_channel=True,
                chat_is_forum=None,
                chat_has_username=None,
                chat_is_created=True,
                user_administrator_rights={"can_post_messages": True}
            )
        )
    ],
    [KeyboardButton(text="🔙 Back to Main")]
], resize_keyboard=True)

# Add to Group keyboard - for /add command (direct invite link)
ADD_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            text="➕ Add Bot to Group",
            url="https://t.me/idfinderpro_bot?startgroup&admin=delete_messages+restrict_members"
        )
    ],
    [
        InlineKeyboardButton(
            text="🔙 Back to Main",
            callback_data="main_menu"
        )
    ]
])

# Donation menu inline keyboard
DONATION_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⭐ Telegram Stars", callback_data='donate_stars'),
        InlineKeyboardButton("💎 TON Crypto", callback_data='donate_ton'),
    ],
    [
        InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')
    ]
])

STARS_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("1 ⭐", callback_data='stars_1'),
        InlineKeyboardButton("5 ⭐", callback_data='stars_5'),
        InlineKeyboardButton("10 ⭐", callback_data='stars_10'),
    ],
    [
        InlineKeyboardButton("20 ⭐", callback_data='stars_20'),
        InlineKeyboardButton("50 ⭐", callback_data='stars_50'),
        InlineKeyboardButton("100 ⭐", callback_data='stars_100'),
    ],
    [
        InlineKeyboardButton("500 ⭐", callback_data='stars_500'),
        InlineKeyboardButton("1000 ⭐", callback_data='stars_1000'),
    ],
    [
        InlineKeyboardButton("🔙 Back", callback_data='back_to_donate')
    ]
])

TON_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("0.1 TON", callback_data='ton_0.1'),
        InlineKeyboardButton("0.2 TON", callback_data='ton_0.2'),
        InlineKeyboardButton("0.5 TON", callback_data='ton_0.5'),
    ],
    [
        InlineKeyboardButton("1 TON", callback_data='ton_1'),
        InlineKeyboardButton("2 TON", callback_data='ton_2'),
    ],
    [
        InlineKeyboardButton("5 TON", callback_data='ton_5'),
        InlineKeyboardButton("10 TON", callback_data='ton_10'),
    ],
    [
        InlineKeyboardButton("🔙 Back", callback_data='back_to_donate')
    ]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name

    # Clear any notification in progress
    if 'notification' in context.user_data:
        context.user_data.pop('notification', None)

    # Add user to database
    user_db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    await update.message.reply_text(
        f"👋 Welcome to ID Finder Pro Bot! {user_name}\n\n"
        f"🔍 This bot helps you find the **Telegram ID** of any:\n"
        f"• 👤 User\n"
        f"• 👥 Group\n"
        f"• 📢 Channel\n"
        f"• 🤖 Bot\n\n"
        f"✅ Just forward a message from any of the above, or select an option below to share a chat.\n\n"
        f"To Get your own id Just Hit /id\n\n"
        f"📣 Official Channel: @idfinderpro",
        parse_mode='Markdown',
        reply_markup=MAIN_KEYBOARD
    )

    return SELECTING_ENTITY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information about how to use the bot"""
    chat_type = update.effective_chat.type

    if chat_type == 'private':
        # Private chat help
        help_text = (
            "📚 <b>ID Finder Pro Bot - Help Guide</b>\n\n"
            "<b>🔍 Basic Commands:</b>\n"
            "• /start - Start the bot and show the main menu\n"
            "• /id - Get your own Telegram ID\n"
            "• /find [user_id] - Find user info by their Telegram ID\n"
            "• /username - Get ID by username (e.g., /username @telegram)\n"
            "• /admin - Show groups and channels you admin\n"
            "• /add - Add the bot to your groups or channels\n"
            "• /help - Show this help message\n"
            "• /donate - Support the developer\n\n"

            "<b>📋 How to Get IDs:</b>\n"
            "1️⃣ <b>Forward a message</b> from any user, bot, group or channel\n"
            "2️⃣ <b>Forward a story</b> from any user or channel\n"
            "3️⃣ Use the <b>buttons</b> to select and share a user, bot, group or channel\n"
            "4️⃣ Use <b>/username</b> command followed by a username (e.g., /username @telegram)\n"
            "5️⃣ Use <b>/find</b> command with a user ID (e.g., /find 123456789)\n"
            "6️⃣ Use <b>/admin</b> to see IDs of groups and channels you administer\n\n"

            "<b>💡 Pro Tips:</b>\n"
            "• For private chats without username, forward a message from them\n"
            "• For public entities, you can use the /username command\n"
            "• Use /find to get detailed info about any user by their ID\n"
            "• Add the bot to groups for advanced group management features\n"
            "• Use the 'Donate' button to support the developer\n\n"

            "<b>🛡️ Group Features:</b>\n"
            "When added to groups, this bot provides:\n"
            "• User identification and info commands\n"
            "• Advanced moderation tools for admins\n"
            "• Warning and mute systems\n"
            "• Group statistics and management\n\n"

            "📣 <b>Official Channel:</b> @idfinderpro\n"
            "🤖 <b>Bot Username:</b> @IDFinderProBot"
        )

        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    else:
        # Group chat help (delegate to group command)
        await group_help_command(update, context)

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /find command to get user info by Telegram ID"""
    chat_type = update.effective_chat.type

    if not context.args or len(context.args) == 0:
        help_text = (
            "🔍 <b>Find User by ID</b>\n\n"
            "Usage: <code>/find [user_id]</code>\n\n"
            "Example: <code>/find 123456789</code>\n\n"
            "This command will try to find information about a user using their Telegram ID."
        )

        if chat_type == 'private':
            await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(help_text, parse_mode='HTML')

    try:
        user_id = int(context.args[0])
    except ValueError:
        error_text = "❌ Invalid user ID. Please provide a valid numeric Telegram ID."

        if chat_type == 'private':
            await update.message.reply_text(error_text, reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(error_text)

    try:
        # Try to get user info using get_chat
        user_info = await context.bot.get_chat(user_id)

        # Format the response
        response_text = f"✅ <b>User Found</b>\n\n"
        response_text += f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
        response_text += f"👤 <b>Name:</b> {user_info.first_name}"

        if user_info.last_name:
            response_text += f" {user_info.last_name}"

        if user_info.username:
            response_text += f"\n📎 <b>Username:</b> @{user_info.username}"

        # Determine entity type
        if user_info.type == 'private':
            if user_info.is_premium:
                response_text += f"\n🏷️ <b>Type:</b> 👤 User (Premium)"
            else:
                response_text += f"\n🏷️ <b>Type:</b> 👤 User"
        elif user_info.type == 'bot':
            response_text += f"\n🏷️ <b>Type:</b> 🤖 Bot"
        elif user_info.type == 'group':
            response_text += f"\n🏷️ <b>Type:</b> 👥 Group"
        elif user_info.type == 'supergroup':
            response_text += f"\n🏷️ <b>Type:</b> 👥 Supergroup"
        elif user_info.type == 'channel':
            response_text += f"\n🏷️ <b>Type:</b> 📢 Channel"

        if user_info.bio:
            response_text += f"\n📝 <b>Bio:</b> {user_info.bio[:100]}{'...' if len(user_info.bio) > 100 else ''}"

        if chat_type == 'private':
            await update.message.reply_text(response_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(response_text, parse_mode='HTML')

    except Exception as e:
        error_text = (
            f"❌ <b>User Not Found</b>\n\n"
            f"Could not find user with ID: <code>{user_id}</code>\n\n"
            f"<b>Possible reasons:</b>\n"
            f"• User has never interacted with this bot\n"
            f"• User has blocked the bot\n"
            f"• Invalid user ID\n"
            f"• User account deleted\n\n"
            f"<b>Note:</b> The bot can only find users who have previously interacted with it or are in mutual groups."
        )

        if chat_type == 'private':
            await update.message.reply_text(error_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(error_text, parse_mode='HTML')

async def username_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /username command to get ID by username"""
    if context.args and len(context.args) > 0:
        # If username is provided in the command, process it immediately
        username = context.args[0]
        # Remove @ if it's included
        if username.startswith('@'):
            username = username[1:]
        
        # Try to get info about the username
        try:
            # Try resolving with the username as provided
            info = await resolve_username_or_link(context.application, username)
            if info:
                text = format_entity_response(info)
                await update.message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            else:
                await update.message.reply_text(
                    f"❌ Could not find information for username @{username}.\n\n"
                    f"<b>Possible reasons:</b>\n"
                    f"• Username doesn't exist\n"
                    f"• User/channel/group is private\n"
                    f"• Username was recently changed\n"
                    f"• Bot doesn't have access to this entity\n\n"
                    f"<b>Tips:</b>\n"
                    f"• Make sure the username is spelled correctly\n"
                    f"• Try forwarding a message from the user instead",
                    parse_mode='HTML',
                    reply_markup=MAIN_KEYBOARD
                )
        except Exception as e:
            logger.error(f"Error in username_command: {e}")
            await update.message.reply_text(
                f"❌ Error processing username @{username}.\n"
                f"Please make sure it's a valid username and try again.",
                reply_markup=MAIN_KEYBOARD
            )
        return SELECTING_ENTITY
    else:
        # If no username provided, ask for it
        await update.message.reply_text(
            "🔍 <b>Username Lookup</b>\n\n"
            "Please enter a username to get its ID.\n\n"
            "📋 <b>Supported formats:</b>\n"
            "• @username (for users, bots, channels, groups)\n"
            "• username (without @)\n"
            "• t.me/username links\n\n"
            "💡 <b>Works for:</b>\n"
            "✅ Users and Bots\n"
            "✅ Public Groups\n"
            "✅ Public Channels\n\n"
            "Just type the username below:",
            parse_mode='HTML',
            reply_markup=MAIN_KEYBOARD
        )
        return WAITING_FOR_USERNAME

async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle username input after /username command"""
    username = update.message.text.strip()
    
    # Check if it's a back button press
    if username == "🔙 Back to Main":
        await update.message.reply_text(
            "Returning to main menu.",
            reply_markup=MAIN_KEYBOARD
        )
        return SELECTING_ENTITY
    
    # Remove @ if it's included
    if username.startswith('@'):
        username = username[1:]
    
    # Try to get info about the username
    try:
        info = await resolve_username_or_link(context.application, username)
        if info:
            text = format_entity_response(info)
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        else:
            await update.message.reply_text(
                f"❌ Could not find information for username @{username}.\n\n"
                f"<b>Possible reasons:</b>\n"
                f"• Username doesn't exist\n"
                f"• User/channel/group is private\n"
                f"• Username was recently changed\n"
                f"• Bot doesn't have access to this entity\n\n"
                f"<b>Tips:</b>\n"
                f"• Make sure the username is spelled correctly\n"
                f"• Try forwarding a message from the user instead",
                parse_mode='HTML',
                reply_markup=MAIN_KEYBOARD
            )
    except Exception as e:
        logger.error(f"Error in handle_username_input: {e}")
        await update.message.reply_text(
            f"❌ Error processing username @{username}.\n"
            f"Please make sure it's a valid username and try again.",
            reply_markup=MAIN_KEYBOARD
        )
    return SELECTING_ENTITY

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_type = update.effective_chat.type

    # Different behavior for private chats vs groups
    if chat_type == 'private':
        # Private chat - use conversation handler format
        text = (
            f"✅ <b>Entity:</b> User\n"
            f"🔗 <b>Name:</b> {user.first_name}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>"
        )

        if user.username:
            text += f"\n📎 <b>Username:</b> @{user.username}"

        # Always keep the main keyboard visible
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    else:
        # Group chat - use group format (delegate to group command)
        await group_id_command(update, context)

async def handle_user_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Debug: Log message attributes
        logger.info(f"Message attributes: {[attr for attr in dir(update.message) if 'shared' in attr.lower()]}")

        # Extract the shared user information with compatibility handling
        user_id = None

        # Try different attribute names for compatibility
        if hasattr(update.message, 'users_shared') and update.message.users_shared:
            users_shared = update.message.users_shared
            logger.info(f"Found users_shared. Attributes: {dir(users_shared)}")

            # Try different attribute names
            if hasattr(users_shared, 'user_ids') and users_shared.user_ids:
                user_id = users_shared.user_ids[0]
                logger.info(f"Got user_id from user_ids: {user_id}")
            elif hasattr(users_shared, 'users') and users_shared.users:
                user_obj = users_shared.users[0]
                user_id = user_obj.user_id if hasattr(user_obj, 'user_id') else user_obj
                logger.info(f"Got user_id from users: {user_id}")
            elif hasattr(users_shared, 'user_id'):
                user_id = users_shared.user_id
                logger.info(f"Got user_id directly: {user_id}")

        elif hasattr(update.message, 'user_shared') and update.message.user_shared:
            # Single user shared (older API)
            user_shared = update.message.user_shared
            logger.info(f"Found user_shared. Attributes: {dir(user_shared)}")

            if hasattr(user_shared, 'user_id'):
                user_id = user_shared.user_id
                logger.info(f"Got user_id from user_shared.user_id: {user_id}")
            elif hasattr(user_shared, 'user_ids'):
                user_id = user_shared.user_ids[0]
                logger.info(f"Got user_id from user_shared.user_ids: {user_id}")

        if not user_id:
            logger.error("Could not extract user ID from shared user data")
            logger.error(f"Available message attributes: {[attr for attr in dir(update.message) if not attr.startswith('_')]}")
            await update.message.reply_text("Error: No user was shared.", reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY

        logger.info(f"Successfully extracted user ID: {user_id}")
        
        try:
            # Get user information
            user = await context.bot.get_chat(user_id)
            
            # Format the response
            text = (
                f"✅ <b>Entity:</b> {'Bot' if getattr(user, 'is_bot', False) else 'User'}\n"
                f"🔗 <b>Name:</b> {getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>"
            )
            
            if hasattr(user, 'username') and user.username:
                text += f"\n📎 <b>Username:</b> @{user.username}"
            
            # Always keep the main keyboard visible
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            
        except Exception as e:
            # If we can't get the chat, just use the user_id from user_shared
            logger.error(f"Error getting user info via get_chat: {e}")
            
            # Fallback to just showing the ID we received
            text = (
                f"✅ <b>Entity:</b> User/Bot\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"<i>Note: Limited information available for this user.</i>"
            )
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        
    except Exception as e:
        logger.error(f"Error in handle_user_shared: {e}")
        await update.message.reply_text(f"❌ Error: Could not retrieve user information.", reply_markup=MAIN_KEYBOARD)
    
    return SELECTING_ENTITY

async def handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract the shared chat information
        chat_shared = update.message.chat_shared
        if not chat_shared:
            await update.message.reply_text("Error: No chat was shared.", reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        
        chat_id = chat_shared.chat_id
        logger.warning(f"Chat shared with ID: {chat_id}")
        
        # Check the request_id to determine the source
        request_id = getattr(chat_shared, 'request_id', 0)
        is_admin_request = request_id in [5, 6]
        is_add_request = request_id in [7, 8]
        
        try:
            # Get chat information
            chat = await context.bot.get_chat(chat_id)
            
            # Determine the entity type
            if hasattr(chat, 'type'):
                if chat.type == "channel":
                    entity_type = "Channel"
                elif chat.type in ["group", "supergroup"]:
                    entity_type = "Group"
                else:
                    entity_type = "Chat"
            else:
                entity_type = "Chat"
            
            # Format the response
            text = (
                f"✅ <b>Entity:</b> {entity_type}\n"
                f"🔗 <b>Name/Title:</b> {getattr(chat, 'title', 'Unknown')}\n"
                f"🆔 <b>ID:</b> <code>{chat.id}</code>"
            )
            
            if hasattr(chat, 'username') and chat.username:
                text += f"\n📎 <b>Username:</b> @{chat.username}"
            
            # Add special notes based on request type
            if is_admin_request:
                text += f"\n\n<b>Note:</b> You are an administrator in this {entity_type.lower()}."
                keyboard = ADMIN_KEYBOARD
            elif is_add_request:
                # For /add command, directly provide the invite link
                bot_username = (await context.bot.get_me()).username

                # Create appropriate invite link based on entity type
                if entity_type.lower() == "channel":
                    invite_link = f"https://t.me/{bot_username}?startchannel&admin=post_messages+edit_messages+delete_messages"
                else:
                    invite_link = f"https://t.me/{bot_username}?startgroup&admin=delete_messages+restrict_members"

                # Send success message with direct invite link
                chat_name = getattr(chat, 'title', 'Unknown')
                await update.message.reply_text(
                    f"✅ <b>Ready to Add Bot!</b>\n\n"
                    f"📋 <b>Selected {entity_type}:</b> {chat_name}\n"
                    f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                    f"🚀 <b>Click the button below to add the bot:</b>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"➕ Add Bot to {entity_type}", url=invite_link)]
                    ])
                )
                return SELECTING_ENTITY
            else:
                keyboard = MAIN_KEYBOARD
            
            # Send the response with the appropriate keyboard
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
            
        except Exception as e:
            # If we can't get the chat, just use the chat_id from chat_shared
            logger.error(f"Error getting chat info via get_chat: {e}")
            
            # Determine if it's likely a channel based on the ID format
            entity_type = "Channel" if str(chat_id).startswith("-100") else "Group/Chat"
            
            # Fallback to just showing the ID we received
            text = (
                f"✅ <b>Entity:</b> {entity_type}\n"
                f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                f"<i>Note: Limited information available for this chat.</i>"
            )
            
            # Determine which keyboard to show
            if is_admin_request:
                keyboard = ADMIN_KEYBOARD
            elif is_add_request:
                # For /add command, directly provide the invite link
                bot_username = (await context.bot.get_me()).username

                # Create appropriate invite link based on entity type
                if entity_type.lower() == "channel":
                    invite_link = f"https://t.me/{bot_username}?startchannel&admin=post_messages+edit_messages+delete_messages"
                else:
                    invite_link = f"https://t.me/{bot_username}?startgroup&admin=delete_messages+restrict_members"

                # Send success message with direct invite link
                await update.message.reply_text(
                    f"✅ <b>Ready to Add Bot!</b>\n\n"
                    f"📋 <b>Selected {entity_type}:</b> {text.split('Name/Title:</b> ')[1].split('<')[0] if 'Name/Title:</b>' in text else 'Unknown'}\n"
                    f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
                    f"🚀 <b>Click the button below to add the bot:</b>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"➕ Add Bot to {entity_type}", url=invite_link)]
                    ])
                )
                return SELECTING_ENTITY
            else:
                keyboard = MAIN_KEYBOARD
                
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in handle_chat_shared: {e}")
        await update.message.reply_text(f"❌ Error: Could not retrieve chat information.", reply_markup=MAIN_KEYBOARD)
    
    return SELECTING_ENTITY

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back_to_menu':
        # Simply dismiss the inline keyboard
        await query.edit_message_text(
            "ID Finder Pro Bot is ready to use! Select an option from the keyboard below or forward a message.",
            reply_markup=None
        )
        return SELECTING_ENTITY
        
    elif query.data == 'donate' or query.data == 'back_to_donate':
        await query.edit_message_text(
            "💰 Support the Developer\n\n"
            "Your donation helps keep this bot running and improving!\n"
            "Choose your preferred donation method:",
            reply_markup=DONATION_KEYBOARD
        )
        return SELECTING_DONATION_METHOD
        
    elif query.data == 'donate_stars':
        await query.edit_message_text(
            "⭐ Donate with Telegram Stars\n\n"
            "Select the amount of stars you want to donate:",
            reply_markup=STARS_KEYBOARD
        )
        return SELECTING_STARS_AMOUNT
        
    elif query.data == 'donate_ton':
        await query.edit_message_text(
            "💎 Donate with TON Crypto\n\n"
            "Select the amount of TON you want to donate:",
            reply_markup=TON_KEYBOARD
        )
        return SELECTING_TON_AMOUNT
        
    elif query.data.startswith('stars_'):
        amount = int(query.data.split('_')[1])
        chat_id = update.effective_chat.id
        title = "Support ID Finder Pro"
        description = f"Donate {amount} Stars to support the development of ID Finder Pro Bot"
        payload = f"stars_donation_{amount}"
        
        # Create price based on amount (as per your edit)
        prices = [LabeledPrice("Stars", amount)]
        
        try:
            # Send invoice for stars payment
            await context.bot.send_invoice(
                chat_id=chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token="",  # Empty provider token as requested
                currency="XTR",  # XTR for stars
                prices=prices,
                is_flexible=False,
            )
            
            # Edit the original message
            await query.edit_message_text(
                f"⭐ I've sent you an invoice for {amount} Stars.\n"
                f"Please complete the payment process to support the developer.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Donation Menu", callback_data='back_to_donate')],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                ])
            )
        except Exception as e:
            logger.error(f"Error sending invoice: {e}")
            await query.edit_message_text(
                f"Sorry, there was an error processing your stars donation request. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Donation Menu", callback_data='back_to_donate')],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
                ])
            )
        
        return SELECTING_ENTITY
        
    elif query.data.startswith('ton_'):
        amount = float(query.data.split('_')[1])
        # Convert TON amount to nanotons (1 TON = 10^9 nanotons)
        amount_nanotons = int(amount * 1000000000)
        
        # Generate TON payment link with the correct amount in nanotons
        ton_payment_link = f"https://app.tonkeeper.com/transfer/{TON_WALLET}?amount={amount_nanotons}&text=Donation%20to%20ID%20Finder%20Bot"
        
        await query.edit_message_text(
            f"💎 TON Donation - {amount} TON\n\n"
            f"To complete your donation, please click the button below to open TON Keeper and confirm your transaction.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Pay with TON Keeper", url=ton_payment_link)],
                [InlineKeyboardButton("🔙 Back to Donation Menu", callback_data='back_to_donate')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_menu')]
            ])
        )
        return SELECTING_ENTITY

    # Notification system callbacks
    elif query.data == 'notify_add_files':
        await query.edit_message_text(
            "📎 <b>Add Files</b>\n\n"
            "Send files you want to include in the notification:\n"
            "• Photos (JPEG, PNG, GIF)\n"
            "• Videos (MP4)\n"
            "• Documents (PDF, etc.)\n\n"
            "Send files one by one, or skip to the next step:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔘 Add Buttons", callback_data="notify_add_buttons")],
                [InlineKeyboardButton("✅ Preview", callback_data="notify_preview")],
                [InlineKeyboardButton("❌ Cancel", callback_data="notify_cancel")]
            ])
        )
        return NOTIFY_BUTTONS

    elif query.data == 'notify_add_buttons':
        await query.edit_message_text(
            "🔘 <b>Add Buttons</b>\n\n"
            "Send button information in this format:\n"
            "<code>Button Text | https://example.com</code>\n\n"
            "Examples:\n"
            "• Visit Website | https://example.com\n"
            "• Join Channel | https://t.me/channel\n"
            "• Download App | https://play.google.com/store\n\n"
            "Send one button per message:",
            parse_mode='HTML'
        )
        return NOTIFY_BUTTONS

    elif query.data == 'notify_preview':
        return await handle_notify_preview(update, context)

    elif query.data == 'notify_send':
        return await send_notification(update, context)

    elif query.data == 'notify_cancel':
        context.user_data.pop('notification', None)
        await query.edit_message_text(
            "❌ Notification cancelled.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]
            ])
        )
        return SELECTING_ENTITY

    return SELECTING_ENTITY

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = str(update.effective_user.id)

    logger.info(f"handle_message called by user {user_id}")
    logger.info(f"Message type: text={bool(message.text)}, photo={bool(message.photo)}, forward={bool(hasattr(message, 'forward_origin') and message.forward_origin)}")
    logger.info(f"User data notification: {context.user_data.get('notification', {})}")

    # Check if admin has notification in progress and handle forwarded messages during notification
    if user_id in ADMIN_IDS and context.user_data.get('notification', {}).get('in_progress'):
        logger.info(f"Admin {user_id} has notification in progress")
        if message and hasattr(message, 'forward_origin') and message.forward_origin:
            logger.info("Forwarded message detected during notification - showing error")
            await message.reply_text(
                "⚠️ <b>Notification Creation in Progress</b>\n\n"
                "You are currently creating a notification. Forwarded message processing is disabled.\n\n"
                "Please:\n"
                "• Complete the notification process, or\n"
                "• Use /start to restart the bot and cancel notification",
                parse_mode='HTML'
            )
            return SELECTING_ENTITY

    # Check if the message is "💰 Donate"
    if message.text == "💰 Donate":
        return await donate_command(update, context)

    # Check if the message is "🔙 Back to Main"
    if message.text == "🔙 Back to Main":
        await message.reply_text("Returning to main menu.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY

    # Handle forwarded messages
    if message and hasattr(message, 'forward_origin') and message.forward_origin:
        try:
            info = await extract_entity_info(message)
            if info:
                text = format_entity_response(info)
                # Always keep the main keyboard visible
                await message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            else:
                await message.reply_text("❌ Could not extract entity info from this forwarded message.", reply_markup=MAIN_KEYBOARD)
        except Exception as e:
            logger.error(f"Error extracting entity info: {e}")
            await message.reply_text("❌ An error occurred while processing the forwarded message.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY

    # For all other messages, show a helpful message with the main keyboard
    await message.reply_text(
        "Please forward a message from a user, channel, group, or bot to get its ID.\n\n"
        "You can also use the /id command to get your own ID or use the buttons below.",
        reply_markup=MAIN_KEYBOARD
    )
    return SELECTING_ENTITY

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return
    info = await resolve_username_or_link(context.application, query)
    text = format_entity_response(info)
    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Fetch Telegram ID",
            input_message_content=InputTextMessageContent(text, parse_mode='HTML'),  # Changed to HTML
            description="Get Telegram ID for @username or t.me link"
        )
    ]
    await update.inline_query.answer(results, cache_time=1)

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 Support the Developer\n\n"
        "Your donation helps keep this bot running and improving!\n"
        "Choose your preferred donation method:",
        reply_markup=DONATION_KEYBOARD
    )
    return SELECTING_DONATION_METHOD

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive bot information and statistics"""
    chat_type = update.effective_chat.type

    # Get user count from database
    total_users = user_db.get_user_count()

    # Get bot info
    bot_info = await context.bot.get_me()

    info_text = (
        f"🤖 <b>{bot_info.first_name} - Bot Information</b>\n\n"
        f"📊 <b>Statistics:</b>\n"
        f"• Total Users: {total_users:,}\n"
        f"• Bot Username: @{bot_info.username}\n"
        f"• Bot ID: <code>{bot_info.id}</code>\n\n"

        f"🔧 <b>Features:</b>\n"
        f"• User, Bot, Group & Channel ID lookup\n"
        f"• Username to ID resolution\n"
        f"• Forwarded message analysis\n"
        f"• Story forwarding support\n"
        f"• Group management tools\n"
        f"• Admin moderation system\n"
        f"• Warning & mute systems\n"
        f"• User database tracking\n\n"

        f"⚡ <b>Supported Methods:</b>\n"
        f"• Forward messages/stories\n"
        f"• Share contacts via buttons\n"
        f"• Username lookup (/username)\n"
        f"• User ID search (/find)\n"
        f"• Admin panel (/admin)\n\n"

        f"🛡️ <b>Group Commands:</b>\n"
        f"• User info & identification\n"
        f"• Moderation tools for admins\n"
        f"• Warning system with tracking\n"
        f"• Temporary mute functionality\n"
        f"• Kick/ban management\n"
        f"• Group statistics\n\n"

        f"💝 <b>Support:</b>\n"
        f"• Developer: Contact via /donate\n"
        f"• Channel: @idfinderpro\n"
        f"• Version: 2.0 Pro\n"
        f"• Last Update: December 2024"
    )

    if chat_type == 'private':
        await update.message.reply_text(info_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    else:
        await update.message.reply_text(info_text, parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed bot statistics (admin only)"""
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    # Check if user is admin
    if user_id not in ADMIN_IDS:
        error_text = "❌ This command is only available to bot administrators."

        if chat_type == 'private':
            await update.message.reply_text(error_text, reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(error_text)
            return

    # Get detailed statistics
    total_users = user_db.get_user_count()
    recent_users = user_db.get_recent_users(7)  # Last 7 days

    # Get bot info
    bot_info = await context.bot.get_me()

    # Calculate uptime (approximate)
    from datetime import datetime
    current_time = datetime.now()

    stats_text = (
        f"📊 <b>Bot Statistics - Admin Panel</b>\n\n"
        f"🤖 <b>Bot Info:</b>\n"
        f"• Name: {bot_info.first_name}\n"
        f"• Username: @{bot_info.username}\n"
        f"• ID: <code>{bot_info.id}</code>\n"
        f"• Can Join Groups: {'✅' if bot_info.can_join_groups else '❌'}\n"
        f"• Can Read Messages: {'✅' if bot_info.can_read_all_group_messages else '❌'}\n\n"

        f"👥 <b>User Statistics:</b>\n"
        f"• Total Users: {total_users:,}\n"
        f"• New Users (7 days): {len(recent_users):,}\n"
        f"• Growth Rate: {(len(recent_users)/max(total_users-len(recent_users), 1)*100):.1f}%\n\n"

        f"⚡ <b>System Info:</b>\n"
        f"• Report Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"• Database Status: ✅ Active\n"
        f"• Bot Status: ✅ Running\n\n"

        f"🔧 <b>Features Active:</b>\n"
        f"• ID Lookup: ✅\n"
        f"• Username Resolution: ✅\n"
        f"• Group Management: ✅\n"
        f"• Admin Notifications: ✅\n"
        f"• User Database: ✅\n"
        f"• Payment System: ✅\n\n"

        f"📈 <b>Usage Metrics:</b>\n"
        f"• Commands Available: 20+\n"
        f"• Group Commands: 15+\n"
        f"• Admin Commands: 10+\n"
        f"• Supported Chat Types: All\n\n"

        f"🛡️ <b>Admin Panel:</b>\n"
        f"• Total Admins: {len(ADMIN_IDS)}\n"
        f"• Your ID: <code>{user_id}</code>\n"
        f"• Access Level: Full Admin"
    )

    if chat_type == 'private':
        await update.message.reply_text(stats_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    else:
        await update.message.reply_text(stats_text, parse_mode='HTML')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show groups and channels where the user is an admin"""
    await update.message.reply_text(
        "👮‍♂️ <b>Admin Mode</b>\n\n"
        "Select a group or channel where you're an administrator to get its ID.\n\n"
        "Note: Only groups and channels where you have admin rights will be shown.",
        parse_mode='HTML',
        reply_markup=ADMIN_KEYBOARD
    )
    return SELECTING_ENTITY

async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer the PreCheckoutQuery"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm the successful payment"""
    payment_info = update.message.successful_payment
    amount = payment_info.total_amount  # No need to divide by 100 since we're using direct amount
    user_name = update.effective_user.first_name

    # Sweet donation success message
    await update.message.reply_text(
        f"🎉 <b>Donation Successful!</b> 🎉\n\n"
        f"💖 Thank you so much, {user_name}! Your generous donation of {amount} ⭐ stars means the world to us!\n\n"
        f"🚀 <b>Your contribution helps us:</b>\n"
        f"• Keep the bot running 24/7\n"
        f"• Add new amazing features\n"
        f"• Provide faster and better service\n"
        f"• Support our development team\n\n"
        f"🌟 You're now part of our amazing supporter community! We're incredibly grateful for your kindness and support.\n\n"
        f"💝 <b>With heartfelt thanks,</b>\n"
        f"The ID Finder Pro Team ❤️",
        parse_mode='HTML',
        reply_markup=MAIN_KEYBOARD
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    await update.message.reply_text("🛠 Admin Panel\nCommands:\n/stats - Show usage stats\n/broadcast <msg> - Broadcast message", reply_markup=MAIN_KEYBOARD)
    return SELECTING_ENTITY

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY

    # Get real stats from user database
    total_users = user_db.get_total_users()
    recent_users = user_db.get_recent_users(5)

    stats_text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📈 Messages Processed: N/A\n"
        f"🔍 ID Lookups: N/A\n"
        f"💰 Donations Received: N/A\n\n"
        f"📅 Recent Users ({len(recent_users)}):\n"
    )

    for user in recent_users:
        name = user.get('first_name', 'Unknown')
        username = user.get('username', '')
        username_text = f"@{username}" if username else "No username"
        joined_date = user.get('joined_date', '')[:10] if user.get('joined_date') else 'Unknown'
        stats_text += f"• {name} ({username_text}) - {joined_date}\n"

    await update.message.reply_text(stats_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
    return SELECTING_ENTITY

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view total users and last 10 joined users"""
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY

    total_users = user_db.get_total_users()
    recent_users = user_db.get_recent_users(10)

    users_text = (
        f"👥 <b>User Statistics</b>\n\n"
        f"📊 <b>Total Users:</b> {total_users}\n\n"
        f"🆕 <b>Last 10 Joined Users:</b>\n"
    )

    if not recent_users:
        users_text += "No users found in database."
    else:
        for i, user in enumerate(recent_users, 1):
            name = user.get('first_name', 'Unknown')
            last_name = user.get('last_name', '')
            full_name = f"{name} {last_name}".strip()
            username = user.get('username', '')
            username_text = f"@{username}" if username else "No username"
            user_id_text = user.get('user_id', 'Unknown')
            joined_date = user.get('joined_date', '')

            # Format date
            if joined_date:
                try:
                    date_obj = datetime.fromisoformat(joined_date)
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    formatted_date = joined_date[:16]
            else:
                formatted_date = 'Unknown'

            users_text += f"{i}. <b>{full_name}</b>\n"
            users_text += f"   ID: <code>{user_id_text}</code>\n"
            users_text += f"   Username: {username_text}\n"
            users_text += f"   Joined: {formatted_date}\n\n"

    await update.message.reply_text(users_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
    return SELECTING_ENTITY

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to start notification creation process"""
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY

    # Initialize notification data
    context.user_data['notification'] = {
        'text': '',
        'entities': [],  # Store original formatting entities
        'files': [],
        'buttons': [],
        'in_progress': True  # Flag to indicate notification is in progress
    }

    await update.message.reply_text(
        "📢 <b>Create Notification</b>\n\n"
        "Step 1/3: Send your notification content.\n\n"
        "You can:\n"
        "• Send text with Telegram formatting (<b>Bold</b>, <i>Italic</i>, <u>Underlined</u>, <s>Strikethrough</s>, <code>Monospace</code>, <a href='url'>Links</a>)\n"
        "• Send files (photos, videos, documents) with optional caption\n"
        "• Send both text and files\n\n"
        "📝 Send your content now:",
        parse_mode='HTML'
    )
    return NOTIFY_TEXT

async def handle_notify_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle notification content input (text and/or files)"""
    try:
        message = update.message
        logger.info(f"handle_notify_text called with message type: {type(message)}")

        # Ensure notification data exists
        if 'notification' not in context.user_data:
            logger.error("Notification data not found in context.user_data")
            await message.reply_text(
                "❌ Session expired. Please use /notify to start again.",
                reply_markup=MAIN_KEYBOARD
            )
            return SELECTING_ENTITY

        notification = context.user_data['notification']
        logger.info(f"Current notification data: {notification}")

        # Handle text message
        if message.text:
            notification['text'] = message.text
            notification['entities'] = message.entities or []  # Preserve original formatting
            content_type = "Text"
            preview = message.text
            logger.info(f"Text message processed: {message.text[:50]}...")
            logger.info(f"Entities preserved: {len(notification['entities'])} formatting entities")

        # Handle photo with optional caption
        elif message.photo:
            file_info = {
                'type': 'photo',
                'file_id': message.photo[-1].file_id,
                'caption': message.caption or '',
                'caption_entities': message.caption_entities or []
            }
            notification['files'].append(file_info)
            notification['text'] = message.caption or ''
            notification['entities'] = message.caption_entities or []
            content_type = "Photo"
            preview = f"📷 Photo with caption: {message.caption}" if message.caption else "📷 Photo (no caption)"
            logger.info(f"Photo processed with caption: {message.caption}")

        # Handle video with optional caption
        elif message.video:
            file_info = {
                'type': 'video',
                'file_id': message.video.file_id,
                'caption': message.caption or '',
                'caption_entities': message.caption_entities or []
            }
            notification['files'].append(file_info)
            notification['text'] = message.caption or ''
            notification['entities'] = message.caption_entities or []
            content_type = "Video"
            preview = f"🎥 Video with caption: {message.caption}" if message.caption else "🎥 Video (no caption)"
            logger.info(f"Video processed with caption: {message.caption}")

        # Handle document with optional caption
        elif message.document:
            file_info = {
                'type': 'document',
                'file_id': message.document.file_id,
                'filename': message.document.file_name,
                'caption': message.caption or '',
                'caption_entities': message.caption_entities or []
            }
            notification['files'].append(file_info)
            notification['text'] = message.caption or ''
            notification['entities'] = message.caption_entities or []
            content_type = "Document"
            preview = f"📎 {file_info['filename']} with caption: {message.caption}" if message.caption else f"📎 {file_info['filename']} (no caption)"
            logger.info(f"Document processed: {file_info['filename']}")

        else:
            logger.warning(f"Unsupported message type received")
            await message.reply_text(
                "❌ Unsupported content type. Please send:\n"
                "• Text message\n"
                "• Photo (with optional caption)\n"
                "• Video (with optional caption)\n"
                "• Document (with optional caption)"
            )
            return NOTIFY_TEXT

        # Success - show options for next step
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔘 Add Buttons", callback_data="notify_add_buttons")],
            [InlineKeyboardButton("✅ Preview & Send", callback_data="notify_preview")],
            [InlineKeyboardButton("❌ Cancel", callback_data="notify_cancel")]
        ])

        await message.reply_text(
            f"✅ {content_type} saved!\n\n"
            f"<b>Preview:</b>\n{preview}\n\n"
            f"Step 2/3: Add inline buttons (optional)\n"
            f"Choose an option:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        return NOTIFY_BUTTONS

    except Exception as e:
        logger.error(f"Error in handle_notify_text: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

        await message.reply_text(
            "❌ An error occurred while processing your content. Please try again or use /start to restart.",
            reply_markup=MAIN_KEYBOARD
        )
        return SELECTING_ENTITY



async def handle_notify_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button input for notification"""
    text = update.message.text

    # Parse button format: "Button Text | https://example.com"
    if '|' in text:
        parts = text.split('|', 1)
        button_text = parts[0].strip()
        button_url = parts[1].strip()

        if button_text and button_url:
            button_info = {
                'text': button_text,
                'url': button_url
            }
            context.user_data['notification']['buttons'].append(button_info)

            await update.message.reply_text(
                f"🔘 Button added: {button_text}\n\n"
                f"Add more buttons or continue:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Preview", callback_data="notify_preview")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="notify_cancel")]
                ])
            )
        else:
            await update.message.reply_text(
                "❌ Invalid format. Use: Button Text | https://example.com"
            )
    else:
        await update.message.reply_text(
            "❌ Invalid format. Use: Button Text | https://example.com\n\n"
            "Example: Visit Website | https://example.com"
        )

    return NOTIFY_BUTTONS

async def handle_notify_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show notification preview and confirm sending"""
    query = update.callback_query
    await query.answer()

    notification = context.user_data.get('notification', {})
    text = notification.get('text', '')
    files = notification.get('files', [])
    buttons = notification.get('buttons', [])

    total_users = user_db.get_total_users()

    # Show button details
    button_details = ""
    if buttons:
        button_details = "\n<b>Buttons:</b>\n"
        for i, btn in enumerate(buttons, 1):
            button_details += f"{i}. {btn['text']} → {btn['url']}\n"

    preview_text = (
        f"📋 <b>Notification Preview</b>\n\n"
        f"<b>Text:</b>\n{text}\n\n"
        f"<b>Files:</b> {len(files)} attached\n"
        f"{button_details}\n"
        f"<b>Recipients:</b> {total_users} users\n\n"
        f"Are you sure you want to send this notification?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send Notification", callback_data="notify_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="notify_cancel")]
    ])

    await query.edit_message_text(preview_text, parse_mode='HTML', reply_markup=keyboard)
    return NOTIFY_CONFIRM

async def send_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send notification to all users"""
    query = update.callback_query
    await query.answer()

    notification = context.user_data.get('notification', {})
    text = notification.get('text', '')
    entities = notification.get('entities', [])  # Original formatting entities
    files = notification.get('files', [])
    buttons = notification.get('buttons', [])

    # Create inline keyboard if buttons exist
    keyboard = None
    if buttons:
        button_rows = []
        for button in buttons:
            button_rows.append([InlineKeyboardButton(button['text'], url=button['url'])])
        keyboard = InlineKeyboardMarkup(button_rows)

    # Get all user IDs
    user_ids = user_db.get_all_user_ids()

    sent_count = 0
    failed_count = 0

    await query.edit_message_text(
        f"📤 Starting to send notification to {len(user_ids)} users...",
        parse_mode='HTML'
    )

    for user_id in user_ids:
        try:
            # Send files with captions if any
            if files:
                for file_info in files:
                    caption = file_info.get('caption', '')
                    caption_entities = file_info.get('caption_entities', [])

                    if file_info['type'] == 'photo':
                        await context.bot.send_photo(
                            user_id,
                            file_info['file_id'],
                            caption=caption,
                            caption_entities=caption_entities,
                            reply_markup=keyboard
                        )
                    elif file_info['type'] == 'video':
                        await context.bot.send_video(
                            user_id,
                            file_info['file_id'],
                            caption=caption,
                            caption_entities=caption_entities,
                            reply_markup=keyboard
                        )
                    elif file_info['type'] == 'document':
                        await context.bot.send_document(
                            user_id,
                            file_info['file_id'],
                            caption=caption,
                            caption_entities=caption_entities,
                            reply_markup=keyboard
                        )
            else:
                # Send text message with original formatting entities
                await context.bot.send_message(
                    user_id,
                    text,
                    entities=entities,  # Use original entities instead of parse_mode
                    reply_markup=keyboard
                )
            sent_count += 1

        except Exception as e:
            logger.warning(f"Failed to send notification to user {user_id}: {e}")
            failed_count += 1

    # Clean up notification data
    context.user_data.pop('notification', None)

    result_text = (
        f"✅ <b>Notification Sent!</b>\n\n"
        f"📊 <b>Results:</b>\n"
        f"• Successfully sent: {sent_count}\n"
        f"• Failed: {failed_count}\n"
        f"• Total users: {len(user_ids)}"
    )

    await context.bot.send_message(
        query.from_user.id,
        result_text,
        parse_mode='HTML',
        reply_markup=MAIN_KEYBOARD
    )
    return SELECTING_ENTITY

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>", reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    # Placeholder: In production, iterate over user DB
    await update.message.reply_text(f"Broadcasted: {' '.join(context.args)} (not implemented)", reply_markup=MAIN_KEYBOARD)
    return SELECTING_ENTITY

async def handle_user_shared_from_other_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user shared from donation or other non-main screens"""
    await update.message.reply_text(
        "⚠️ <b>Feature Not Available Here</b>\n\n"
        "You tried to share a user, but this feature is only available from the main menu.\n\n"
        "💡 <b>To use ID finder features:</b>\n"
        "1. Click the button below to return to main menu\n"
        "2. Use the main menu options to find IDs\n\n"
        "Or simply send /start to restart the bot.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ])
    )
    return SELECTING_ENTITY

async def handle_chat_shared_from_other_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat shared from donation or other non-main screens"""
    await update.message.reply_text(
        "⚠️ <b>Feature Not Available Here</b>\n\n"
        "You tried to share a group/channel, but this feature is only available from the main menu.\n\n"
        "💡 <b>To use ID finder features:</b>\n"
        "1. Click the button below to return to main menu\n"
        "2. Use the main menu options to find IDs\n\n"
        "Or simply send /start to restart the bot.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ])
    )
    return SELECTING_ENTITY

async def handle_message_from_other_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages or other content from donation or other non-main screens"""
    await update.message.reply_text(
        "⚠️ <b>Feature Not Available Here</b>\n\n"
        "You tried to use an ID finder feature, but this is only available from the main menu.\n\n"
        "💡 <b>To use ID finder features:</b>\n"
        "1. Click the button below to return to main menu\n"
        "2. Use the main menu options to find IDs\n"
        "3. Forward messages or share users/groups from there\n\n"
        "Or simply send /start to restart the bot.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ])
    )
    return SELECTING_ENTITY

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add command to add the bot to a group"""
    await update.message.reply_text(
        "🚀 <b>Add Bot to Group</b>\n\n"
        "Click the button below to add this bot directly to your group.\n\n"
        "📋 <b>Requirements:</b>\n"
        "• You must be an admin in the group\n"
        "• You must have permission to invite users\n"
        "• The bot will be added with delete messages and restrict members permissions\n\n"
        "💡 <b>How it works:</b>\n"
        "1. Click the 'Add Bot to Group' button\n"
        "2. Select the group from your list\n"
        "3. The bot will be automatically added!\n\n"
        "📚 <b>After adding:</b> Use /help_group in your group for user commands help.\n\n"
        "No need to send the group back to the bot - it's that simple! 🎉",
        parse_mode='HTML',
        reply_markup=ADD_KEYBOARD
    )
    return SELECTING_ENTITY

async def ids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the ID of the current group"""
    # Only work in groups
    chat_type = update.effective_chat.type
    if chat_type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "This command can only be used in groups.",
            reply_markup=MAIN_KEYBOARD
        )
        return SELECTING_ENTITY
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    chat_username = update.effective_chat.username
    
    text = (
        f"✅ <b>Group Information</b>\n\n"
        f"🔗 <b>Title:</b> {chat_title}\n"
        f"🆔 <b>ID:</b> <code>{chat_id}</code>"
    )
    
    if chat_username:
        text += f"\n📎 <b>Username:</b> @{chat_username}"
    
    await update.message.reply_text(text, parse_mode='HTML')
    return SELECTING_ENTITY

async def mem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command for admins to get member info in groups"""
    # Check if command is used in a group
    chat_type = update.effective_chat.type
    if chat_type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "This command can only be used in groups.",
            reply_markup=MAIN_KEYBOARD
        )
        return SELECTING_ENTITY
    
    # Check if user is an admin
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Get user's member status
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
        
        if not is_admin:
            await update.message.reply_text(
                "❌ This command is only available to group administrators.",
                reply_markup=MAIN_KEYBOARD
            )
            return SELECTING_ENTITY
        
        # If no arguments, show help
        if not context.args:
            await update.message.reply_text(
                "👮‍♂️ <b>Member ID Finder</b>\n\n"
                "Use this command to get information about group members.\n\n"
                "<b>Usage:</b>\n"
                "• <code>/mem @username</code> - Get info by username\n"
                "• <code>/mem user_id</code> - Get info by user ID\n"
                "• <code>/mem</code> - Reply to a message to get info about its sender\n\n"
                "This command is only available to group administrators.",
                parse_mode='HTML'
            )
            return SELECTING_ENTITY
        
        # Process the argument (username or ID)
        arg = context.args[0]
        
        # Try to get member info
        try:
            # Check if it's a user ID
            if arg.isdigit() or (arg.startswith('-') and arg[1:].isdigit()):
                user_id_to_check = int(arg)
                member_info = await context.bot.get_chat_member(chat_id, user_id_to_check)
                user = member_info.user
            else:
                # It's a username
                if arg.startswith('@'):
                    username = arg[1:]
                else:
                    username = arg
                
                # First get the user ID from the username
                user = await context.bot.get_chat(username)
                user_id_to_check = user.id
                # Then get the member info
                member_info = await context.bot.get_chat_member(chat_id, user_id_to_check)
            
            # Format the response
            status = member_info.status
            
            text = (
                f"✅ <b>Member Information</b>\n\n"
                f"👤 <b>Name:</b> {user.first_name}"
            )
            
            if user.last_name:
                text += f" {user.last_name}"
                
            text += f"\n🆔 <b>User ID:</b> <code>{user.id}</code>"
            
            if user.username:
                text += f"\n📎 <b>Username:</b> @{user.username}"
                
            text += f"\n📊 <b>Status:</b> {status.capitalize()}"
            
            if status == "administrator":
                text += " (Admin)"
            elif status == "creator":
                text += " (Owner)"
                
            # Send the response
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error getting member info: {e}")
            await update.message.reply_text(
                f"❌ Error: Could not find member with identifier '{arg}' in this group.",
                parse_mode='HTML'
            )
        
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await update.message.reply_text(
            "❌ An error occurred while checking your permissions.",
            reply_markup=MAIN_KEYBOARD
        )
    
    return SELECTING_ENTITY

def main():
    # Print startup message
    print("ID Finder Pro Bot is starting...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Define separate command sets for private chats and groups
    private_commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("id", "Get your own ID"),
        BotCommand("find", "Find user info by ID"),
        BotCommand("username", "Get ID by username"),
        BotCommand("admin", "Show groups/channels you admin"),
        BotCommand("add", "Add bot to your groups"),
        BotCommand("info", "Show bot information"),
        BotCommand("stats", "Show bot statistics (admin only)"),
        BotCommand("help", "Show help information"),
        BotCommand("help_group", "Show group commands help"),
        BotCommand("help_admin", "Show admin commands help"),
        BotCommand("donate", "Support the developer")
    ]

    group_commands = [
        BotCommand("id", "Get your own ID"),
        BotCommand("ids", "Get group ID"),
        BotCommand("find", "Find user info by ID"),
        BotCommand("whois", "Get user info"),
        BotCommand("mentionid", "Create clickable mention"),
        BotCommand("info", "Show bot information"),
        BotCommand("help_group", "Show group help"),
        BotCommand("help_admin", "Show admin help")
    ]
    
    # Create conversation handler with per_message=False to avoid warnings
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('id', get_user_id),
            CommandHandler('find', find_command),
            CommandHandler('info', info_command),
            CommandHandler('stats', stats_command),
            CommandHandler('admin', admin_command),
            CommandHandler('username', username_command),
            CommandHandler('donate', donate_command),
            CommandHandler('add', add_command),
            CommandHandler('mem', mem_command),
            CommandHandler('ids', ids_command),
            CommandHandler('notify', notify_command),
            CommandHandler('help_group', help_group_command),
            CommandHandler('help_admin', help_admin_command),
        ],
        states={
            SELECTING_ENTITY: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared),
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_message),
            ],
            SELECTING_CHAT: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared),
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_message),
            ],
            SELECTING_DONATION_METHOD: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared_from_other_screen),
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared_from_other_screen),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_message_from_other_screen),
            ],
            SELECTING_STARS_AMOUNT: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared_from_other_screen),
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared_from_other_screen),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_message_from_other_screen),
            ],
            SELECTING_TON_AMOUNT: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.StatusUpdate.USERS_SHARED, handle_user_shared_from_other_screen),
                MessageHandler(filters.StatusUpdate.CHAT_SHARED, handle_chat_shared_from_other_screen),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_message_from_other_screen),
            ],
            WAITING_FOR_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input),
            ],
            WAITING_FOR_MEMBER_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input),
            ],
            NOTIFY_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notify_text),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_notify_text),
            ],
            NOTIFY_BUTTONS: [
                CallbackQueryHandler(menu_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notify_buttons),
            ],
            NOTIFY_CONFIRM: [
                CallbackQueryHandler(menu_callback),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('id', get_user_id),
            CommandHandler('find', find_command),
            CommandHandler('info', info_command),
            CommandHandler('stats', stats_command),
            CommandHandler('admin', admin_command),
            CommandHandler('username', username_command),
            CommandHandler('donate', donate_command),
            CommandHandler('add', add_command),
            CommandHandler('mem', mem_command),
            CommandHandler('ids', ids_command),
            CommandHandler('notify', notify_command),
            CommandHandler('help_group', help_group_command),
            CommandHandler('help_admin', help_admin_command),
        ],
        per_message=False,
    )
    
    # Add all handlers that are not part of the conversation
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('users', users_command))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(InlineQueryHandler(inline_query_handler))

    # Add group command handlers
    # User commands (available to everyone in groups)
    application.add_handler(CommandHandler('find', find_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('info', info_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('ids', group_ids_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('whois', whois_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('mentionid', mentionid_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('help_group', help_group_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('help_admin', help_admin_command, filters=filters.ChatType.GROUPS))

    # Admin commands (only for group admins)
    application.add_handler(CommandHandler('warn', warn_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('warnings', warnings_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('resetwarn', resetwarn_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('mute', mute_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('unmute', unmute_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('kick', kick_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('ban', ban_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('unban', unban_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('pin', pin_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('groupinfo', groupinfo_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('listadmins', listadmins_command, filters=filters.ChatType.GROUPS))
    
    # Add payment handlers
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    
    # Set commands using the post_init method
    async def post_init(app: Application) -> None:
        # Set commands for private chats
        await app.bot.set_my_commands(
            private_commands,
            scope={'type': 'all_private_chats'}
        )

        # Set commands for groups
        await app.bot.set_my_commands(
            group_commands,
            scope={'type': 'all_group_chats'}
        )

        print("Bot commands have been set for private chats and groups!")

    # Set the post_init function
    application.post_init = post_init
    
    # Print ready message
    print("Bot is ready! Press Ctrl+C to stop.")
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main() 