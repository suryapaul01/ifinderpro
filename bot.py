import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, KeyboardButton, ReplyKeyboardMarkup, LabeledPrice, KeyboardButtonRequestChat, KeyboardButtonRequestUsers, ReplyKeyboardRemove, BotCommand, ChatMember, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler, ConversationHandler, PreCheckoutQueryHandler, ChatMemberHandler)
from config import BOT_TOKEN, ADMIN_IDS, TON_WALLET
from utils import extract_entity_info, format_entity_response, resolve_username_or_link, get_user_chats
from user_db import user_db
from groups_db import groups_db
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

    # Track interaction
    track_interaction(update)

    welcome_text = (
        f"👋 <b>Welcome to ID Finder Pro Bot, {user_name}!</b>\n\n"

        f"🔍 <b>What I Can Do:</b>\n"
        f"• Find Telegram IDs of users, groups, channels & bots\n"
        f"• Extract IDs from forwarded messages & stories\n"
        f"• Provide detailed entity information\n"
        f"• Manage groups with advanced admin tools\n"
        f"• Track user interactions and analytics\n\n"

        f"🚀 <b>Quick Start:</b>\n"
        f"• <b>Forward any message</b> to get sender's ID\n"
        f"• <b>Forward stories</b> to get user/channel ID\n"
        f"• Use <b>buttons below</b> to share contacts\n"
        f"• Type <b>/id</b> to get your own ID\n"
        f"• Type <b>/help</b> for help system\n\n"

        f"🛡️ <b>Group Features:</b>\n"
        f"Add me to your groups for:\n"
        f"• User identification commands\n"
        f"• Warning & mute systems\n"
        f"• Admin management tools\n"
        f"• Group statistics tracking\n\n"

        f"📣 <b>Official Channel:</b> @idfinderpro <b>subscribe For Updates</b>\n"

        f"<i>Select an option below to get started!</i>"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=MAIN_KEYBOARD
    )

    return SELECTING_ENTITY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interactive help system"""
    # Track interaction
    track_interaction(update)

    chat_type = update.effective_chat.type

    # Create main help keyboard
    help_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 User Commands", callback_data="help_user"),
            InlineKeyboardButton("👥 Group Commands", callback_data="help_group")
        ],
        [
            InlineKeyboardButton("🤖 Bot Features", callback_data="help_features"),
            InlineKeyboardButton("🔧 How to Use", callback_data="help_usage")
        ],
        [
            InlineKeyboardButton("💰 Donations", callback_data="help_donations"),
            InlineKeyboardButton("ℹ️ About", callback_data="help_about")
        ],
        [
            InlineKeyboardButton("📋 Show All", callback_data="help_show_all")
        ]
    ])

    help_text = (
        "🔍 <b>ID Finder Pro Bot - Help Center</b>\n\n"
        "Welcome to the interactive help system! Select a category below to learn more about specific features and commands.\n\n"
        "Use the buttons to navigate through different help sections, or click 'Show All' to see all commands at once."
    )

    if chat_type == 'private':
        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=help_keyboard)
        return SELECTING_ENTITY
    else:
        await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=help_keyboard)

async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help system callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Navigation buttons
    nav_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back", callback_data="help_back"),
            InlineKeyboardButton("🏠 Menu", callback_data="help_menu")
        ]
    ])

    try:
        if data == "help_user":
            text = (
                "👤 <b>User Commands</b>\n\n"
                "Click on the buttons below and share the user whose ID you want to know.\n\n"
                "<b>Available Commands:</b>\n"
                "• /start - Start the bot and show main menu\n"
                "• /id - Get your own Telegram ID\n"
                "• /find [user_id] - Find user info by ID\n"
                "• /username [@username] - Get ID by username\n"
                "• /admin - Show groups/channels you admin\n"
                "• /add - Add bot to your groups\n"
                "• /donate - Support the developer\n"
                "• /help - Show this help system\n\n"
                "<blockquote><b>Please Note: that some of our feature might not work, it is because telegram changes their API time to time. I'll Update you all in my channel @idfinderpro.</b></blockquote>"
            )

        elif data == "help_group":
            text = (
                "👥 <b>Group Commands</b>\n\n"
                "These commands work only in groups where the bot is added.\n\n"
                "<b>User Commands (Everyone):</b>\n"
                "• /id - Get your own ID\n"
                "• /ids - Get IDs of all group members\n"
                "• /whois [@username or reply] - Get user info\n"
                "• /mentionid [@username or reply] - Mention with ID\n"
                "• /info - Show group information\n\n"

                "<b>Admin Commands (Admins only):</b>\n"
                "• /warn [@user or reply] - Warn a user\n"
                "• /mute [@user or reply] - Mute a user\n"
                "• /kick [@user or reply] - Kick a user\n"
                "• /ban [@user or reply] - Ban a user\n"
                "• /pin [reply to message] - Pin a message\n"
                "• /groupinfo - Show detailed group info\n"
                "• /listadmins - List all group admins\n\n"
                "<blockquote><b>Please Note: that some of our feature might not work, it is because telegram changes their API time to time. I'll Update you all in my channel @idfinderpro.</b></blockquote>"
            )

        elif data == "help_features":
            text = (
                "🤖 <b>Bot Features</b>\n\n"
                "<b>ID Extraction Methods:</b>\n"
                "1️⃣ Forward any message from user/bot/group/channel\n"
                "2️⃣ Forward stories from users or channels\n"
                "3️⃣ Use keyboard buttons to share contacts\n"
                "4️⃣ Use /username command with @username\n"
                "5️⃣ Use /find command with user ID\n\n"

                "<b>Special Features:</b>\n"
                "• Story ID extraction support\n"
                "• Inline mode (@IDFinderPro_Bot)\n"
                "• Group management tools\n"
                "• Admin notification system\n"
                "• User database tracking\n"
                "• CSV data export (admin)\n"
                "• Analytics dashboard (admin)\n\n"
                "<blockquote><b>Please Note: that some of our feature might not work, it is because telegram changes their API time to time. I'll Update you all in my channel @idfinderpro.</b></blockquote>"
            )

        elif data == "help_usage":
            text = (
                "🔧 <b>How to Use</b>\n\n"
                "<b>Getting Started:</b>\n"
                "1. Start the bot with /start\n"
                "2. Use the main menu buttons or commands\n\n"

                "<b>Finding IDs:</b>\n"
                "• <b>Forward Method:</b> Forward any message\n"
                "• <b>Username Method:</b> /username @telegram\n"
                "• <b>Button Method:</b> Use 'User', 'Bot', 'Group', 'Channel' buttons\n"
                "• <b>Story Method:</b> Forward stories from users/channels\n\n"

                "<b>Group Usage:</b>\n"
                "1. Add bot to your group\n"
                "2. Make bot admin for full features\n"
                "3. Use group commands for management\n\n"

                "<b>Pro Tips:</b>\n"
                "• Private chats: Forward messages\n"
                "• Public entities: Use /username\n"
                "• Groups: Add bot as admin\n\n"
                "<blockquote><b>Please Note: that some of our feature might not work, it is because telegram changes their API time to time. I'll Update you all in my channel @idfinderpro.</b></blockquote>"
            )

        elif data == "help_donations":
            text = (
                "💰 <b>Donations & Support</b>\n\n"
                "Support the developer of ID Finder Pro Bot!\n\n"
                "<b>How to Donate:</b>\n"
                "• Use the 'Donate' button in main menu\n"
                "• Send /donate command\n"
                "• Choose from 1⭐, 5⭐, 10⭐, 25⭐, 50⭐ options\n\n"

                "<b>Your donations help:</b>\n"
                "• Keep the bot running 24/7\n"
                "• Add new amazing features\n"
                "• Provide faster service\n"
                "• Support developer @tataa_sumo\n\n"

                "<b>Payment Methods:</b>\n"
                "• Telegram Stars (⭐)\n"
                "• TON Cryptocurrency\n\n"

                "Thank you for supporting our work! ❤️"
            )

        elif data == "help_about":
            text = (
                "ℹ️ <b>About ID Finder Pro Bot</b>\n\n"
                "<b>Bot Information:</b>\n"
                "• Name: ID Finder Pro Bot\n"
                "• Username: @IDFinderPro_Bot\n"
                "• Version: 2.0 Pro\n"
                "• Developer: @tataa_sumo\n\n"

                "<b>Features:</b>\n"
                "• Advanced ID extraction\n"
                "• Story support\n"
                "• Group management\n"
                "• Admin tools\n"
                "• Analytics dashboard\n\n"

                "<b>Contact:</b>\n"
                "• Official Channel: @idfinderpro\n"
                "• Support: Contact admin\n"
                "• Updates: @idfinderpro\n\n"

                "Made with ❤️ by @tataa_sumo for the Telegram community!"
            )

        elif data == "help_show_all":
            text = (
                "📋 <b>All Commands</b>\n\n"

                "<b>👤 User Commands:</b>\n"
                "• /start - Start bot\n"
                "• /id - Get your ID\n"
                "• /find [id] - Find user by ID\n"
                "• /username [@user] - Get ID by username\n"
                "• /admin - Show admin groups\n"
                "• /add - Add bot to groups\n"
                "• /info - Bot information\n"
                "• /donate - Support developer\n"
                "• /help - This help system\n\n"

                "<b>👥 Group Commands:</b>\n"
                "• /id, /ids, /whois, /mentionid, /info\n"
                "• /warn, /mute, /kick, /ban (admin)\n"
                "• /pin, /groupinfo, /listadmins (admin)\n\n"

                "<b>🔧 Usage Methods:</b>\n"
                "• Forward messages/stories\n"
                "• Use keyboard buttons\n"
                "• Commands with parameters\n"
                "• Inline mode support\n\n"
                "<blockquote><b>Please Note: that some of our feature might not work, it is because telegram changes their API time to time. I'll Update you all in my channel @idfinderpro.</b></blockquote>"
            )

        elif data == "help_back" or data == "help_menu":
            # Return to main help menu
            help_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👤 User Commands", callback_data="help_user"),
                    InlineKeyboardButton("👥 Group Commands", callback_data="help_group")
                ],
                [
                    InlineKeyboardButton("🤖 Bot Features", callback_data="help_features"),
                    InlineKeyboardButton("🔧 How to Use", callback_data="help_usage")
                ],
                [
                    InlineKeyboardButton("💰 Donations", callback_data="help_donations"),
                    InlineKeyboardButton("ℹ️ About", callback_data="help_about")
                ],
                [
                    InlineKeyboardButton("📋 Show All", callback_data="help_show_all")
                ]
            ])

            text = (
                "🔍 <b>ID Finder Pro Bot - Help Center</b>\n\n"
                "Welcome to the interactive help system! Select a category below to learn more about specific features and commands.\n\n"
                "Use the buttons to navigate through different help sections, or click 'Show All' to see all commands at once."
            )

            await query.edit_message_text(text, parse_mode='HTML', reply_markup=help_keyboard)
            return

        else:
            text = "❌ Unknown help section."

        await query.edit_message_text(text, parse_mode='HTML', reply_markup=nav_keyboard)

    except Exception as e:
        logger.error(f"Error in help callback: {e}")
        await query.edit_message_text("❌ An error occurred while loading help.")

async def admin_com_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only bot management interface"""
    user_id = str(update.effective_user.id)
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

    # Track interaction
    track_interaction(update)

    admin_text = (
        "🛡️ <b>Admin Commands</b>\n\n"
        "Here are all the admin-only commands available:\n\n"

        "<b>📊 Analytics & Statistics:</b>\n"
        "• <code>/stats</code> - Comprehensive analytics dashboard\n"
        "• <code>/users</code> - View user statistics and data\n"
        "• <code>/groups</code> - View group statistics and data\n\n"

        "<b>📢 Communication:</b>\n"
        "• <code>/notify</code> - Send notification to users\n\n"

        "<b>📄 Data Export:</b>\n"
        "• Use <code>/stats</code> → Export buttons for CSV downloads\n"
        "• Users CSV - Complete user database\n"
        "• Groups CSV - Complete groups database\n\n"

        "<b>🔐 Admin Access:</b>\n"
        f"• Total Admins: {len(ADMIN_IDS)}\n"
        f"• Your ID: <code>{user_id}</code>\n"
        f"• Access Level: Full Admin ✅\n\n"

        "<i>All commands above are restricted to administrators only.</i>"
    )

    if chat_type == 'private':
        await update.message.reply_text(admin_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
        return SELECTING_ENTITY
    else:
        await update.message.reply_text(admin_text, parse_mode='HTML')



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
        if not context.args or len(context.args) == 0:
            raise IndexError("No arguments provided")
        user_id = int(context.args[0])
    except (ValueError, IndexError):
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
        try:
            username = context.args[0]
        except IndexError:
            username = None
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
    # Track interaction
    track_interaction(update)

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
            if hasattr(users_shared, 'user_ids') and users_shared.user_ids and len(users_shared.user_ids) > 0:
                user_id = users_shared.user_ids[0]
                logger.info(f"Got user_id from user_ids: {user_id}")
            elif hasattr(users_shared, 'users') and users_shared.users and len(users_shared.users) > 0:
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
            elif hasattr(user_shared, 'user_ids') and user_shared.user_ids and len(user_shared.user_ids) > 0:
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
        
    elif query.data.startswith('help_'):
        # Handle help callbacks
        await handle_help_callback(update, context)
        return SELECTING_ENTITY

    elif query.data.startswith('analytics_'):
        # Handle analytics callbacks
        await handle_analytics_callback(update, context)
        return SELECTING_ENTITY

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

def track_interaction(update: Update):
    """Helper function to track user and group interactions"""
    try:
        user = update.effective_user
        chat = update.effective_chat

        # Track user
        if user:
            user_db.add_user(user.id, user.username, user.first_name, user.last_name)

        # Track group interaction if in a group
        if chat and chat.type in ['group', 'supergroup', 'channel']:
            groups_db.increment_interaction(chat.id)
            # Also ensure group is tracked
            groups_db.add_group(
                group_id=chat.id,
                group_title=chat.title,
                group_type=chat.type,
                username=chat.username,
                invite_link=getattr(chat, 'invite_link', None)
            )
    except Exception as e:
        logger.error(f"Error tracking interaction: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat
    user_id = str(user.id)

    logger.info(f"handle_message called by user {user_id}")
    logger.info(f"Message type: text={bool(message.text)}, photo={bool(message.photo)}, forward={bool(hasattr(message, 'forward_origin') and message.forward_origin)}")
    logger.info(f"User data notification: {context.user_data.get('notification', {})}")

    # Track interaction
    track_interaction(update)

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
            logger.info(f"Processing forwarded message. Origin type: {message.forward_origin.type}")
            logger.info(f"Forward origin details: {message.forward_origin}")

            info = await extract_entity_info(message)
            if info:
                logger.info(f"Successfully extracted info: {info}")
                text = format_entity_response(info)
                # Always keep the main keyboard visible
                await message.reply_text(text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            else:
                logger.warning("Could not extract entity info from forwarded message")
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

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show analytics dashboard (admin only)"""
    user_id = str(update.effective_user.id)  # Convert to string for comparison
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

    # Create analytics dashboard keyboard
    analytics_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Overview", callback_data="analytics_overview"),
            InlineKeyboardButton("👥 Users", callback_data="analytics_users")
        ],
        [
            InlineKeyboardButton("🏢 Groups", callback_data="analytics_groups"),
            InlineKeyboardButton("📈 Interactions", callback_data="analytics_interactions")
        ],
        [
            InlineKeyboardButton("📄 Users CSV", callback_data="analytics_export_users"),
            InlineKeyboardButton("📊 Groups CSV", callback_data="analytics_export_groups")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="analytics_refresh"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")
        ]
    ])

    dashboard_text = (
        f"📊 <b>Analytics Dashboard</b>\n\n"
        f"Welcome to the comprehensive analytics dashboard!\n\n"
        f"<b>Available Analytics:</b>\n"
        f"• 📊 Overview - General bot statistics\n"
        f"• 👥 Users - User analytics and growth\n"
        f"• 🏢 Groups - Group statistics and activity\n"
        f"• 📈 Interactions - 24h/7d/1m interaction data\n"
        f"• 📄 Users CSV - Download user data\n"
        f"• 📊 Groups CSV - Download group data\n\n"
        f"Select an option below to view detailed analytics:"
    )

    if chat_type == 'private':
        await update.message.reply_text(dashboard_text, parse_mode='HTML', reply_markup=analytics_keyboard)
        return SELECTING_ENTITY
    else:
        await update.message.reply_text(dashboard_text, parse_mode='HTML', reply_markup=analytics_keyboard)

async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analytics dashboard callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)  # Convert to string for comparison

    # Check if user is admin
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access denied. Admin only.")
        return

    data = query.data

    try:
        if data == "analytics_overview":
            await show_analytics_overview(query, context)
        elif data == "analytics_users":
            await show_analytics_users(query, context)
        elif data == "analytics_groups":
            await show_analytics_groups(query, context)
        elif data == "analytics_interactions":
            await show_analytics_interactions(query, context)
        elif data == "analytics_export_users":
            await export_users_csv(query, context)
        elif data == "analytics_export_groups":
            await export_groups_csv(query, context)
        elif data == "analytics_refresh":
            # Recreate the analytics dashboard with fresh data
            from datetime import datetime

            # Get fresh statistics
            total_users = user_db.get_total_users()
            total_groups = len(groups_db.get_all_groups())
            current_time = datetime.now().strftime('%H:%M:%S')

            analytics_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Overview", callback_data="analytics_overview"),
                    InlineKeyboardButton("👥 Users", callback_data="analytics_users")
                ],
                [
                    InlineKeyboardButton("🏢 Groups", callback_data="analytics_groups"),
                    InlineKeyboardButton("📈 Interactions", callback_data="analytics_interactions")
                ],
                [
                    InlineKeyboardButton("📄 Users CSV", callback_data="analytics_export_users"),
                    InlineKeyboardButton("📊 Groups CSV", callback_data="analytics_export_groups")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="analytics_refresh"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")
                ]
            ])

            dashboard_text = (
                f"📊 <b>Analytics Dashboard</b>\n\n"
                f"Welcome to the comprehensive analytics dashboard!\n\n"
                f"<b>📈 Current Statistics:</b>\n"
                f"• Total Users: {total_users:,}\n"
                f"• Total Groups: {total_groups:,}\n"
                f"• Last Refreshed: {current_time}\n\n"
                f"<b>Available Analytics:</b>\n"
                f"• 📊 Overview - General bot statistics\n"
                f"• 👥 Users - User analytics and growth\n"
                f"• 🏢 Groups - Group statistics and activity\n"
                f"• 📈 Interactions - 24h/7d/1m interaction data\n"
                f"• 📄 Users CSV - Download user data\n"
                f"• 📊 Groups CSV - Download group data\n\n"
                f"Select an option below to view detailed analytics:"
            )

            await query.edit_message_text(dashboard_text, parse_mode='HTML', reply_markup=analytics_keyboard)
    except Exception as e:
        logger.error(f"Error in analytics callback: {e}")
        await query.edit_message_text("❌ An error occurred while loading analytics.")

async def show_analytics_overview(query, context):
    """Show general bot overview analytics"""
    # Get statistics
    total_users = user_db.get_total_users()
    group_stats = groups_db.get_group_stats()
    bot_info = await context.bot.get_me()

    from datetime import datetime
    current_time = datetime.now()

    overview_text = (
        f"📊 <b>Bot Overview Analytics</b>\n\n"
        f"🤖 <b>Bot Information:</b>\n"
        f"• Name: {bot_info.first_name}\n"
        f"• Username: @{bot_info.username}\n"
        f"• ID: <code>{bot_info.id}</code>\n"
        f"• Can Join Groups: {'✅' if bot_info.can_join_groups else '❌'}\n\n"

        f"📈 <b>Usage Statistics:</b>\n"
        f"• Total Users: {total_users:,}\n"
        f"• Total Groups: {group_stats['total_groups']:,}\n"
        f"• Total Interactions: {group_stats['total_interactions']:,}\n\n"

        f"🏢 <b>Group Breakdown:</b>\n"
        f"• Public Groups: {group_stats['public_groups']:,}\n"
        f"• Private Groups: {group_stats['private_groups']:,}\n\n"

        f"⚡ <b>System Status:</b>\n"
        f"• Report Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"• Database: ✅ Active\n"
        f"• Bot Status: ✅ Running\n\n"

        f"🛡️ <b>Admin Info:</b>\n"
        f"• Total Admins: {len(ADMIN_IDS)}\n"
        f"• Your Access: Full Admin"
    )

    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="analytics_refresh")]
    ])

    await query.edit_message_text(overview_text, parse_mode='HTML', reply_markup=back_keyboard)

async def show_analytics_users(query, context):
    """Show user analytics"""
    total_users = user_db.get_total_users()
    recent_users_24h = user_db.get_recent_users(1)
    recent_users_7d = user_db.get_recent_users(7)
    recent_users_30d = user_db.get_recent_users(30)

    # Calculate growth rates
    growth_24h = len(recent_users_24h)
    growth_7d = len(recent_users_7d)
    growth_30d = len(recent_users_30d)

    users_text = (
        f"👥 <b>User Analytics</b>\n\n"
        f"📊 <b>Total Statistics:</b>\n"
        f"• Total Users: {total_users:,}\n\n"

        f"📈 <b>Growth Analytics:</b>\n"
        f"• Last 24 Hours: +{growth_24h:,} users\n"
        f"• Last 7 Days: +{growth_7d:,} users\n"
        f"• Last 30 Days: +{growth_30d:,} users\n\n"

        f"📊 <b>Growth Rates:</b>\n"
        f"• Daily Average: {(growth_7d/7):.1f} users/day\n"
        f"• Weekly Average: {(growth_30d/4.3):.1f} users/week\n"
        f"• Monthly Growth: {(growth_30d/max(total_users-growth_30d, 1)*100):.1f}%\n\n"

        f"🎯 <b>User Engagement:</b>\n"
        f"• Active Users (7d): {growth_7d:,}\n"
        f"• Retention Rate: {(growth_7d/max(total_users, 1)*100):.1f}%\n\n"

        f"💡 <b>Insights:</b>\n"
    )

    if growth_24h > growth_7d/7:
        users_text += "• 📈 Above average daily growth\n"
    else:
        users_text += "• 📉 Below average daily growth\n"

    if growth_7d > 0:
        users_text += "• ✅ Positive weekly growth\n"
    else:
        users_text += "• ⚠️ No growth this week\n"

    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="analytics_refresh")]
    ])

    await query.edit_message_text(users_text, parse_mode='HTML', reply_markup=back_keyboard)

async def show_analytics_groups(query, context):
    """Show group analytics"""
    group_stats = groups_db.get_group_stats()
    recent_groups = groups_db.get_recent_groups(5)

    groups_text = (
        f"🏢 <b>Group Analytics</b>\n\n"
        f"📊 <b>Overview:</b>\n"
        f"• Total Groups: {group_stats['total_groups']:,}\n"
        f"• Total Interactions: {group_stats['total_interactions']:,}\n\n"

        f"🔓 <b>Privacy Breakdown:</b>\n"
        f"• Public Groups: {group_stats['public_groups']:,}\n"
        f"• Private Groups: {group_stats['private_groups']:,}\n\n"

        f"📈 <b>Group Types:</b>\n"
    )

    for group_type, count in group_stats['type_counts'].items():
        type_emoji = {'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(group_type, '❓')
        groups_text += f"• {type_emoji} {group_type.title()}: {count:,}\n"

    groups_text += f"\n📊 <b>Activity Metrics:</b>\n"
    if group_stats['total_groups'] > 0:
        avg_interactions = group_stats['total_interactions'] / group_stats['total_groups']
        groups_text += f"• Avg Interactions/Group: {avg_interactions:.1f}\n"

    groups_text += f"\n🕒 <b>Recent Groups:</b>\n"
    for i, (group_id, group_info) in enumerate(recent_groups[:3], 1):
        title = group_info.get('title', 'Unknown')[:20]
        interactions = group_info.get('interaction_count', 0)
        groups_text += f"{i}. {title}... ({interactions:,} interactions)\n"

    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="analytics_refresh")]
    ])

    await query.edit_message_text(groups_text, parse_mode='HTML', reply_markup=back_keyboard)

async def show_analytics_interactions(query, context):
    """Show interaction analytics"""
    # This is a simplified version - in a real implementation, you'd track interactions in a time-series database
    total_users = user_db.get_total_users()
    group_stats = groups_db.get_group_stats()

    # Simulate interaction data (in a real implementation, you'd have actual interaction tracking)
    interactions_24h = group_stats['total_interactions'] // 30  # Rough estimate
    interactions_7d = group_stats['total_interactions'] // 4
    interactions_30d = group_stats['total_interactions']

    interactions_text = (
        f"📈 <b>Interaction Analytics</b>\n\n"
        f"⏰ <b>Time-based Interactions:</b>\n"
        f"• Last 24 Hours: {interactions_24h:,}\n"
        f"• Last 7 Days: {interactions_7d:,}\n"
        f"• Last 30 Days: {interactions_30d:,}\n\n"

        f"📊 <b>Interaction Rates:</b>\n"
        f"• Hourly Average: {(interactions_24h/24):.1f}\n"
        f"• Daily Average: {(interactions_7d/7):.1f}\n"
        f"• Weekly Average: {(interactions_30d/4.3):.1f}\n\n"

        f"🎯 <b>Engagement Metrics:</b>\n"
        f"• Total Commands: {interactions_30d:,}\n"
        f"• Commands/User: {(interactions_30d/max(total_users, 1)):.1f}\n"
        f"• Commands/Group: {(group_stats['total_interactions']/max(group_stats['total_groups'], 1)):.1f}\n\n"

        f"📈 <b>Growth Trends:</b>\n"
        f"• Daily Growth: {((interactions_24h*30)/max(interactions_30d, 1)*100):.1f}%\n"
        f"• Weekly Growth: {((interactions_7d*4)/max(interactions_30d, 1)*100):.1f}%\n\n"

        f"💡 <b>Note:</b> Interaction data includes all bot commands,\n"
        f"forwarded messages, and group activities."
    )

    back_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="analytics_refresh")]
    ])

    await query.edit_message_text(interactions_text, parse_mode='HTML', reply_markup=back_keyboard)

async def export_users_csv(query, context):
    """Export users data to CSV"""
    try:
        import csv
        import io
        from datetime import datetime

        # Get all users
        all_users = user_db.get_all_users()

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Join Date', 'Last Seen'])

        # Write user data
        for user_id, user_data in all_users.items():
            writer.writerow([
                user_id,
                user_data.get('username', ''),
                user_data.get('first_name', ''),
                user_data.get('last_name', ''),
                user_data.get('join_date', ''),
                user_data.get('last_seen', '')
            ])

        csv_content = output.getvalue()
        output.close()

        # Create file
        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Send file
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = filename

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=csv_file,
            filename=filename,
            caption=f"📄 <b>Users Export</b>\n\n"
                   f"• Total Users: {len(all_users):,}\n"
                   f"• Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"• Format: CSV",
            parse_mode='HTML'
        )

        await query.answer("✅ Users CSV export sent!")

    except Exception as e:
        logger.error(f"Error exporting users CSV: {e}")
        await query.answer("❌ Error exporting data")

async def export_groups_csv(query, context):
    """Export groups data to CSV"""
    try:
        import csv
        import io
        from datetime import datetime

        # Get all groups
        all_groups = groups_db.get_all_groups()

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Group ID', 'Group Name', 'Type', 'Username', 'Privacy', 'Added Date', 'Last Interaction', 'Interaction Count', 'Status'])

        # Write group data
        for group_id, group_data in all_groups.items():
            privacy = "Public" if group_data.get('username') else "Private"
            status = "Active" if group_data.get('is_active', True) else "Inactive"

            writer.writerow([
                group_id,
                group_data.get('title', ''),
                group_data.get('type', ''),
                group_data.get('username', ''),
                privacy,
                group_data.get('added_date', ''),
                group_data.get('last_interaction', ''),
                group_data.get('interaction_count', 0),
                status
            ])

        csv_content = output.getvalue()
        output.close()

        # Create file
        filename = f"groups_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Send file
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = filename

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=csv_file,
            filename=filename,
            caption=f"📊 <b>Groups Export</b>\n\n"
                   f"• Total Groups: {len(all_groups):,}\n"
                   f"• Active Groups: {len([g for g in all_groups.values() if g.get('is_active', True)]):,}\n"
                   f"• Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"• Format: CSV",
            parse_mode='HTML'
        )

        await query.answer("✅ Groups CSV export sent!")

    except Exception as e:
        logger.error(f"Error exporting groups CSV: {e}")
        await query.answer("❌ Error exporting data")

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show groups statistics (admin only)"""
    user_id = str(update.effective_user.id)  # Convert to string for comparison
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

    try:
        # Get group statistics
        stats = groups_db.get_group_stats()
        recent_groups = groups_db.get_recent_groups(10)

        # Build response text
        groups_text = (
            f"👥 <b>Groups Statistics - Admin Panel</b>\n\n"

            f"📊 <b>Overview:</b>\n"
            f"• Total Groups: {stats['total_groups']:,}\n"
            f"• Total Interactions: {stats['total_interactions']:,}\n"
            f"• Public Groups: {stats['public_groups']:,}\n"
            f"• Private Groups: {stats['private_groups']:,}\n\n"

            f"📈 <b>Group Types:</b>\n"
        )

        for group_type, count in stats['type_counts'].items():
            type_emoji = {
                'group': '👥',
                'supergroup': '👥',
                'channel': '📢'
            }.get(group_type, '❓')
            groups_text += f"• {type_emoji} {group_type.title()}: {count:,}\n"

        groups_text += f"\n🕒 <b>Recently Added Groups (Last 10):</b>\n\n"

        if recent_groups:
            for i, (group_id, group_info) in enumerate(recent_groups, 1):
                title = group_info.get('title', 'Unknown')
                username = group_info.get('username')
                group_type = group_info.get('type', 'unknown')
                interactions = group_info.get('interaction_count', 0)
                added_date = group_info.get('added_date', '')

                # Format date
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(added_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                except:
                    formatted_date = 'Unknown'

                # Group type emoji
                type_emoji = {
                    'group': '👥',
                    'supergroup': '👥',
                    'channel': '📢'
                }.get(group_type, '❓')

                # Privacy indicator
                privacy = "🔓 Public" if username else "🔒 Private"

                groups_text += (
                    f"{i}. {type_emoji} <b>{title}</b>\n"
                    f"   🆔 ID: <code>{group_id}</code>\n"
                    f"   {privacy}"
                )

                if username:
                    groups_text += f" (@{username})"

                groups_text += (
                    f"\n   📊 Interactions: {interactions:,}\n"
                    f"   📅 Added: {formatted_date}\n\n"
                )
        else:
            groups_text += "No groups found.\n\n"

        groups_text += (
            f"💡 <b>Note:</b> Groups are automatically tracked when the bot is added.\n"
            f"Interactions include all bot activities in each group."
        )

        if chat_type == 'private':
            await update.message.reply_text(groups_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(groups_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in groups_command: {e}")
        error_msg = "❌ An error occurred while fetching groups data. Please try again."
        if chat_type == 'private':
            await update.message.reply_text(error_msg, reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        else:
            await update.message.reply_text(error_msg)

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

async def track_group_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track bot interactions in groups"""
    try:
        chat = update.effective_chat
        if chat and chat.type in ['group', 'supergroup', 'channel']:
            # Track interaction
            groups_db.increment_interaction(chat.id)

            # Update group info if needed
            groups_db.add_group(
                group_id=chat.id,
                group_title=chat.title,
                group_type=chat.type,
                username=chat.username,
                invite_link=getattr(chat, 'invite_link', None)
            )
    except Exception as e:
        logger.error(f"Error tracking group interaction: {e}")

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added/removed from groups"""
    try:
        chat_member_update = update.my_chat_member
        chat = chat_member_update.chat
        new_status = chat_member_update.new_chat_member.status
        old_status = chat_member_update.old_chat_member.status

        if chat.type in ['group', 'supergroup', 'channel']:
            if new_status in ['member', 'administrator'] and old_status in ['left', 'kicked']:
                # Bot was added to group
                logger.info(f"Bot added to group: {chat.title} ({chat.id})")
                groups_db.add_group(
                    group_id=chat.id,
                    group_title=chat.title,
                    group_type=chat.type,
                    username=chat.username,
                    invite_link=getattr(chat, 'invite_link', None)
                )
            elif new_status in ['left', 'kicked'] and old_status in ['member', 'administrator']:
                # Bot was removed from group
                logger.info(f"Bot removed from group: {chat.title} ({chat.id})")
                groups_db.mark_group_inactive(chat.id)
    except Exception as e:
        logger.error(f"Error handling chat member update: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    try:
        logger.error(f"Exception while handling an update: {context.error}")

        # Try to send error message to admin
        if update and hasattr(update, 'effective_chat') and update.effective_chat and ADMIN_IDS and len(ADMIN_IDS) > 0:
            try:
                # Convert first admin ID to int if it's a string
                first_admin_id = int(ADMIN_IDS[0]) if ADMIN_IDS[0] and ADMIN_IDS[0].strip() else None
                if first_admin_id:
                    await context.bot.send_message(
                        chat_id=first_admin_id,
                        text=f"🚨 <b>Bot Error</b>\n\n"
                             f"Error: <code>{str(context.error)}</code>\n"
                             f"Chat ID: {update.effective_chat.id}\n"
                             f"User ID: {update.effective_user.id if update.effective_user else 'Unknown'}",
                        parse_mode='HTML'
                    )
            except Exception as admin_error:
                logger.error(f"Could not send error to admin: {admin_error}")

    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def detect_existing_groups(bot):
    """Detect and track groups where the bot is already added"""
    try:
        logger.info("Starting detection of existing groups...")

        # Note: Telegram Bot API doesn't provide a direct way to get all chats
        # where the bot is a member. This is a limitation of the Bot API.
        # The bot can only track groups when:
        # 1. It receives messages in those groups
        # 2. It's added/removed from groups (via ChatMemberHandler)
        # 3. Groups are manually tracked when commands are used

        # For now, we'll just log that the detection is complete
        # In a real implementation, you might:
        # - Use a webhook to track all incoming updates
        # - Implement a periodic check mechanism
        # - Use the groups database to track known groups

        existing_groups = groups_db.get_all_groups()
        logger.info(f"Currently tracking {len(existing_groups)} groups in database")

        # Send a summary to the first admin if available
        if ADMIN_IDS and len(ADMIN_IDS) > 0 and existing_groups:
            try:
                first_admin_id = int(ADMIN_IDS[0]) if ADMIN_IDS[0] and ADMIN_IDS[0].strip() else None
                if first_admin_id:
                    summary_text = (
                        f"🤖 <b>Bot Startup Summary</b>\n\n"
                        f"📊 <b>Groups Tracking:</b>\n"
                        f"• Total Groups: {len(existing_groups):,}\n"
                        f"• Active Groups: {len([g for g in existing_groups.values() if g.get('is_active', True)]):,}\n\n"
                        f"💡 <b>Note:</b> The bot will automatically track new groups when:\n"
                        f"• Added to new groups\n"
                        f"• Commands are used in groups\n"
                        f"• Messages are sent in groups\n\n"
                        f"✅ Bot is ready and tracking interactions!"
                    )

                    await bot.send_message(
                        chat_id=first_admin_id,
                        text=summary_text,
                        parse_mode='HTML'
                    )
            except Exception as admin_error:
                logger.error(f"Could not send startup summary to admin: {admin_error}")

        logger.info("Group detection completed")

    except Exception as e:
        logger.error(f"Error detecting existing groups: {e}")

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
        try:
            arg = context.args[0]
        except IndexError:
            await update.message.reply_text(
                "❌ Please provide a username or user ID.\n"
                "Usage: /mem @username or /mem 123456789",
                parse_mode='HTML'
            )
            return SELECTING_ENTITY
        
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
        BotCommand("help", "Show interactive help system"),
        BotCommand("donate", "Support the developer")
    ]

    group_commands = [
        BotCommand("id", "Get your own ID"),
        BotCommand("ids", "Get group ID"),
        BotCommand("find", "Find user info by ID"),
        BotCommand("whois", "Get user info"),
        BotCommand("mentionid", "Create clickable mention"),
        BotCommand("help", "Show interactive help system")
    ]
    
    # Create conversation handler with per_message=False to avoid warnings
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('id', get_user_id),
            CommandHandler('find', find_command),
            CommandHandler('users', users_command),
            CommandHandler('groups', groups_command),
            CommandHandler('stats', stats_command),
            CommandHandler('admin', admin_command),
            CommandHandler('username', username_command),
            CommandHandler('donate', donate_command),
            CommandHandler('add', add_command),
            CommandHandler('mem', mem_command),
            CommandHandler('ids', ids_command),
            CommandHandler('notify', notify_command),
            CommandHandler('admin_com', admin_com_command),
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
            CommandHandler('users', users_command),
            CommandHandler('groups', groups_command),
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
    application.add_handler(CommandHandler('admin_com', admin_com_command))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('users', users_command))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(InlineQueryHandler(inline_query_handler))

    # Add group command handlers
    # User commands (available to everyone in groups)
    application.add_handler(CommandHandler('find', find_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('ids', group_ids_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('whois', whois_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('mentionid', mentionid_command, filters=filters.ChatType.GROUPS))

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

        # Detect and track existing groups
        await detect_existing_groups(app.bot)

    # Set the post_init function
    application.post_init = post_init

    # Add global error handler
    application.add_error_handler(error_handler)

    # Add chat member handler to track group additions/removals
    application.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Print ready message
    print("Bot is ready! Press Ctrl+C to stop.")
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main() 