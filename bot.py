import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, KeyboardButton, ReplyKeyboardMarkup, LabeledPrice, KeyboardButtonRequestChat, KeyboardButtonRequestUsers, ReplyKeyboardRemove, BotCommand, ChatMember, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler, ConversationHandler, PreCheckoutQueryHandler, ChatMemberHandler)
from config import BOT_TOKEN, ADMIN_IDS, TON_WALLET
from utils import extract_entity_info, format_entity_response, resolve_username_or_link, get_user_chats
import uuid

# Set logging level to only show important messages
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # Changed from INFO to WARNING to reduce log output
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_ENTITY, SELECTING_CHAT, SELECTING_DONATION_METHOD, SELECTING_STARS_AMOUNT, SELECTING_TON_AMOUNT, WAITING_FOR_USERNAME, WAITING_FOR_MEMBER_USERNAME = range(7)

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

# Add to Group keyboard - for /add command (simplified to one button)
ADD_KEYBOARD = ReplyKeyboardMarkup([
    [
        KeyboardButton(
            text="➕ Add Bot to Group/Channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=7,
                chat_is_channel=None,  # Allow both groups and channels
                chat_is_forum=None,
                chat_has_username=None,
                chat_is_created=None,  # Allow existing chats
                user_administrator_rights={"can_invite_users": True}
            )
        )
    ],
    [KeyboardButton(text="🔙 Back to Main")]
], resize_keyboard=True)

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
        InlineKeyboardButton("5 ⭐", callback_data='stars_5'),
        InlineKeyboardButton("10 ⭐", callback_data='stars_10'),
        InlineKeyboardButton("20 ⭐", callback_data='stars_20'),
    ],
    [
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
    user_name = update.effective_user.first_name
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
    help_text = (
        "📚 <b>ID Finder Pro Bot - Help Guide</b>\n\n"
        "<b>Basic Commands:</b>\n"
        "• /start - Start the bot and show the main menu\n"
        "• /id - Get your own Telegram ID\n"
        "• /help - Show this help message\n"
        "• /username - Get ID by username (e.g., /username @telegram)\n"
        "• /admin - Show groups and channels you admin\n"
        "• /add - Add the bot to your groups or channels\n"
        "• /donate - Support the developer\n\n"
        
        "<b>Group Commands:</b>\n"
        "• /ids - Show the current group ID\n"
        "• /mem - (Admin only) Get member info in groups\n\n"
        
        "<b>How to Get IDs:</b>\n"
        "1️⃣ <b>Forward a message</b> from any user, bot, group or channel\n"
        "2️⃣ <b>Forward a story</b> from any user or channel\n"
        "3️⃣ Use the <b>buttons</b> to select and share a user, bot, group or channel\n"
        "4️⃣ Use <b>/username</b> command followed by a username (e.g., /username @telegram)\n"
        "5️⃣ Use <b>/admin</b> to see IDs of groups and channels you administer\n\n"
        
        "<b>Tips:</b>\n"
        "• For private chats without username, forward a message from them\n"
        "• For public entities, you can use the /username command\n"
        "• Use the 'Donate' button to support the developer\n\n"
        
        "📣 Official Channel: @idfinderpro"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)
    return SELECTING_ENTITY

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
            "Please enter a username to get its ID.\n"
            "Format: @username or just username",
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
    
    # Create a simple HTML-formatted response instead of Markdown
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

async def handle_user_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract the shared user information
        users_shared = update.message.users_shared
        if not users_shared or not users_shared.user_ids:
            await update.message.reply_text("Error: No user was shared.", reply_markup=MAIN_KEYBOARD)
            return SELECTING_ENTITY
        
        # Get the first user ID (we'll only process the first one if multiple are shared)
        user_id = users_shared.user_ids[0]
        logger.warning(f"User shared with ID: {user_id}")
        
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
    
    return SELECTING_ENTITY

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
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
    
    await update.message.reply_text(
        f"Thank you for your donation of {amount} stars, {user_name}! ⭐\n\n"
        f"Your support helps keep this bot running and improving. "
        f"We appreciate your generosity!",
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
    await update.message.reply_text("📊 Usage stats: (not implemented)", reply_markup=MAIN_KEYBOARD)
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

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add command to add the bot to a group or channel"""
    await update.message.reply_text(
        "🚀 <b>Add Bot to Group or Channel</b>\n\n"
        "Click the button below to select a group or channel where you want to add this bot.\n\n"
        "📋 <b>Requirements:</b>\n"
        "• You must be an admin in the group/channel\n"
        "• You must have permission to invite users\n\n"
        "After selecting, the bot will be automatically added to your chosen group/channel.",
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
    
    # Define commands that will be shown in the bot's menu
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("id", "Get your own ID"),
        BotCommand("username", "Get ID by username"),
        BotCommand("admin", "Show groups/channels you admin"),
        BotCommand("add", "Add bot to your groups"),
        BotCommand("help", "Show help information"),
        BotCommand("donate", "Support the developer")
    ]
    
    # Create conversation handler with per_message=False to avoid warnings
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('id', get_user_id),
            CommandHandler('admin', admin_command),
            CommandHandler('username', username_command),
            CommandHandler('donate', donate_command),
            CommandHandler('add', add_command),
            CommandHandler('mem', mem_command),
            CommandHandler('ids', ids_command),
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
            ],
            SELECTING_STARS_AMOUNT: [
                CallbackQueryHandler(menu_callback),
            ],
            SELECTING_TON_AMOUNT: [
                CallbackQueryHandler(menu_callback),
            ],
            WAITING_FOR_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input),
            ],
            WAITING_FOR_MEMBER_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('id', get_user_id),
            CommandHandler('admin', admin_command),
            CommandHandler('username', username_command),
            CommandHandler('donate', donate_command),
            CommandHandler('add', add_command),
            CommandHandler('mem', mem_command),
            CommandHandler('ids', ids_command),
        ],
        per_message=False,
    )
    
    # Add all handlers that are not part of the conversation
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    # Add payment handlers
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    
    # Set commands using the post_init method
    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(commands)
        print("Bot commands have been set!")
    
    # Set the post_init function
    application.post_init = post_init
    
    # Print ready message
    print("Bot is ready! Press Ctrl+C to stop.")
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main() 