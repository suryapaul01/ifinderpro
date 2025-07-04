from telegram import Message, User, Chat
from telegram.constants import ChatType
import logging
from config import TON_WALLET

logger = logging.getLogger(__name__)

async def extract_entity_info(message: Message):
    """
    Extracts entity info from a forwarded message or chat/user object.
    Returns a dict with type, id, username, name/title, verified.
    """
    try:
        # Handle the new forward_origin attribute (Bot API 7.0+)
        if hasattr(message, 'forward_origin') and message.forward_origin:
            origin_type = message.forward_origin.type
            
            if origin_type == 'user':
                if hasattr(message.forward_origin, 'sender_user'):
                    user_origin = message.forward_origin.sender_user
                    entity_type = 'User' if not user_origin.is_bot else 'Bot'
                    name = f"{user_origin.first_name or ''} {user_origin.last_name or ''}".strip()
                    username = user_origin.username
                    verified = None
                    entity_id = user_origin.id
                    
                    return {
                        'type': entity_type,
                        'id': entity_id,
                        'username': username,
                        'name': name,
                        'verified': verified
                    }
                    
            elif origin_type == 'chat':
                if hasattr(message.forward_origin, 'sender_chat'):
                    chat_origin = message.forward_origin.sender_chat
                    if chat_origin.type == ChatType.CHANNEL:
                        entity_type = 'Channel'
                    elif chat_origin.type == ChatType.GROUP:
                        entity_type = 'Group'
                    elif chat_origin.type == ChatType.SUPERGROUP:
                        entity_type = 'Group'
                    else:
                        entity_type = 'Unknown'
                    name = chat_origin.title
                    username = chat_origin.username
                    verified = getattr(chat_origin, 'is_verified', None)
                    entity_id = chat_origin.id
                    
                    return {
                        'type': entity_type,
                        'id': entity_id,
                        'username': username,
                        'name': name,
                        'verified': verified
                    }
            
            # Handle story origin
            elif origin_type == 'story':
                if hasattr(message.forward_origin, 'sender_user'):
                    # Story from a user
                    user_origin = message.forward_origin.sender_user
                    entity_type = 'User Story'
                    name = f"{user_origin.first_name or ''} {user_origin.last_name or ''}".strip()
                    username = user_origin.username
                    verified = None
                    entity_id = user_origin.id
                    
                    return {
                        'type': entity_type,
                        'id': entity_id,
                        'username': username,
                        'name': name,
                        'verified': verified,
                        'story_id': getattr(message.forward_origin, 'story_id', None)
                    }
                elif hasattr(message.forward_origin, 'sender_chat'):
                    # Story from a channel
                    chat_origin = message.forward_origin.sender_chat
                    entity_type = 'Channel Story'
                    name = chat_origin.title
                    username = chat_origin.username
                    verified = getattr(chat_origin, 'is_verified', None)
                    entity_id = chat_origin.id
                    
                    return {
                        'type': entity_type,
                        'id': entity_id,
                        'username': username,
                        'name': name,
                        'verified': verified,
                        'story_id': getattr(message.forward_origin, 'story_id', None)
                    }
                    
            elif origin_type == 'hidden_user':
                # Handle hidden user origin
                if hasattr(message.forward_origin, 'sender_user_name'):
                    return {
                        'type': 'Hidden User',
                        'id': 'Hidden',
                        'username': None,
                        'name': message.forward_origin.sender_user_name,
                        'verified': None
                    }
                    
            elif origin_type == 'channel':
                # Handle channel origin
                if hasattr(message.forward_origin, 'chat'):
                    chat = message.forward_origin.chat
                    return {
                        'type': 'Channel',
                        'id': chat.id,
                        'username': chat.username,
                        'name': chat.title,
                        'verified': getattr(chat, 'is_verified', None)
                    }
                    
            # Log the forward_origin for debugging
            logger.info(f"Forward origin type: {origin_type}")
            logger.info(f"Forward origin attributes: {dir(message.forward_origin)}")
                
        # Fallback for older versions (deprecated, but kept for compatibility)
        if hasattr(message, 'forward_from') and message.forward_from:
            entity = message.forward_from
            entity_type = 'User' if not entity.is_bot else 'Bot'
            name = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            username = entity.username
            verified = None
            
            return {
                'type': entity_type,
                'id': entity.id,
                'username': username,
                'name': name,
                'verified': verified
            }
            
        elif hasattr(message, 'forward_from_chat') and message.forward_from_chat:
            entity = message.forward_from_chat
            if entity.type == ChatType.CHANNEL:
                entity_type = 'Channel'
            elif entity.type == ChatType.GROUP:
                entity_type = 'Group'
            elif entity.type == ChatType.SUPERGROUP:
                entity_type = 'Group'
            else:
                entity_type = 'Unknown'
            name = entity.title
            username = entity.username
            verified = getattr(entity, 'is_verified', None)
            
            return {
                'type': entity_type,
                'id': entity.id,
                'username': username,
                'name': name,
                'verified': verified
            }
            
        # If we get here, we couldn't extract any entity info
        logger.warning("Could not extract entity info from message")
        if hasattr(message, 'forward_origin'):
            logger.warning(f"Message has forward_origin: {message.forward_origin}")
        if hasattr(message, 'forward_from'):
            logger.warning(f"Message has forward_from: {message.forward_from}")
        if hasattr(message, 'forward_from_chat'):
            logger.warning(f"Message has forward_from_chat: {message.forward_from_chat}")
            
        return None
        
    except Exception as e:
        logger.error(f"Error extracting entity info: {e}")
        return None

def format_entity_response(info: dict) -> str:
    if not info:
        return "❌ Could not extract entity info. Please forward a valid message or send a valid username/link."
    lines = [
        f"✅ <b>Entity Detected:</b> {info['type']}",
        f"🔗 <b>Name/Title:</b> {info['name']}",
    ]
    
    # Only add ID if it's not hidden
    if info['id'] != 'Hidden':
        lines.append(f"🆔 <b>ID:</b> <code>{info['id']}</code>")
        
    if info.get('username'):
        lines.append(f"📎 <b>Username:</b> @{info['username']}")
    if info.get('verified') is not None:
        lines.append(f"✅ <b>Verified:</b> {'Yes' if info['verified'] else 'No'}")
    if info.get('story_id') is not None:
        lines.append(f"📱 <b>Story ID:</b> <code>{info['story_id']}</code>")
    return '\n'.join(lines)

async def resolve_username_or_link(app, text: str):
    """
    Resolves @username or t.me link to a Chat or User object using get_chat.
    Returns entity info dict or None.
    """
    import re
    username = None
    
    # Clean up the input text
    text = text.strip()
    
    if text.startswith('@'):
        username = text[1:]
    else:
        # Match different t.me link formats
        m = re.match(r'(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/|s/|c/)?([a-zA-Z0-9_-]+)', text)
        if m:
            username = m.group(1)
        else:
            # If no @ and not a link, treat as a raw username
            username = text
    
    if not username:
        return None
        
    try:
        # Try to get chat info
        chat = await app.bot.get_chat(username)
        
        # Determine entity type
        if hasattr(chat, 'type'):
            if chat.type == "channel":
                entity_type = "Channel"
            elif chat.type in ["group", "supergroup"]:
                entity_type = "Group"
            elif chat.type == "private":
                entity_type = "Bot" if getattr(chat, 'is_bot', False) else "User"
            else:
                entity_type = chat.type.capitalize()
        else:
            entity_type = "Bot" if getattr(chat, 'is_bot', False) else "User"
        
        # Get name based on entity type
        if entity_type in ["Channel", "Group"]:
            name = getattr(chat, 'title', None) or "Unknown"
        else:
            first_name = getattr(chat, 'first_name', '') or ''
            last_name = getattr(chat, 'last_name', '') or ''
            name = f"{first_name} {last_name}".strip() or "Unknown"
        
        info = {
            'type': entity_type,
            'id': chat.id,
            'username': getattr(chat, 'username', None),
            'name': name,
            'verified': getattr(chat, 'is_verified', None)
        }
        return info
    except Exception as e:
        logger.error(f"Error resolving username or link: {e}")
        return None

async def get_user_chats(bot, user_id, entity_type):
    """
    Get a list of chats that the user has access to based on the entity type.
    Returns a list of chat objects with id and name.
    
    Note: This is a placeholder implementation. In a real bot, you would need to:
    1. For channels/groups: Use the getDialogs method (not available in python-telegram-bot)
    2. For users: Use the getContacts method (not available in python-telegram-bot)
    3. For bots: Use a database of known bots the user has interacted with
    
    This implementation returns a placeholder list for demonstration purposes.
    """
    # This is a placeholder. In a real implementation, you would need to use
    # Telegram API methods not directly exposed in python-telegram-bot
    # or maintain your own database of user interactions.
    
    try:
        if entity_type == 'users':
            # Placeholder for user contacts
            return [
                {'id': '123456789', 'name': 'Sample User 1'},
                {'id': '987654321', 'name': 'Sample User 2'},
                # In a real implementation, you would fetch actual contacts
            ]
        elif entity_type == 'channels':
            # Placeholder for channels
            return [
                {'id': '-1001234567890', 'name': 'Sample Channel 1'},
                {'id': '-1009876543210', 'name': 'Sample Channel 2'},
                # In a real implementation, you would fetch actual channels
            ]
        elif entity_type == 'groups':
            # Placeholder for groups
            return [
                {'id': '-987654321', 'name': 'Sample Group 1'},
                {'id': '-123456789', 'name': 'Sample Group 2'},
                # In a real implementation, you would fetch actual groups
            ]
        elif entity_type == 'bots':
            # Placeholder for bots
            return [
                {'id': '111222333', 'name': 'Sample Bot 1'},
                {'id': '444555666', 'name': 'Sample Bot 2'},
                # In a real implementation, you would fetch actual bots
            ]
        return []
    except Exception as e:
        logger.error(f"Error getting user chats: {e}")
        return []

async def process_donation(bot, user_id, donation_type, amount):
    """
    Process a donation from a user.
    Returns a success message if the donation was processed successfully.
    
    Note: This is a placeholder implementation. In a real bot, you would:
    1. For stars: Use the Telegram Payments API
    2. For TON: Generate a TON payment link and verify the transaction
    """
    try:
        user = await bot.get_chat(user_id)
        user_name = user.first_name
        
        if donation_type == 'stars':
            # In a real implementation, you would use the Telegram Payments API
            return f"Thank you for your donation of {amount} stars, {user_name}! ⭐"
        
        elif donation_type == 'ton':
            # Convert TON amount to nanotons (1 TON = 10^9 nanotons)
            amount_nanotons = int(float(amount) * 1000000000)
            # Generate TON payment link
            ton_payment_link = f"https://app.tonkeeper.com/transfer/{TON_WALLET}?amount={amount_nanotons}&text=Donation%20to%20ID%20Finder%20Bot"
            return ton_payment_link
            
        return "Invalid donation type."
    except Exception as e:
        logger.error(f"Error processing donation: {e}")
        return "Error processing donation. Please try again later." 