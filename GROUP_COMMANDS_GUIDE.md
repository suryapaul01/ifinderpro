# 🛡️ Group Management Commands Guide

## Overview
Your ID Finder Pro Bot now includes comprehensive group management features that work **only in groups and supergroups**. The commands are automatically filtered to work only in group chats.

## 📁 New Files Added
- `group_commands.py` - All group command handlers
- `group_db.py` - Database for warnings, mutes, and moderation data
- `group_data.json` - JSON database file (created automatically)

## 👤 User Commands (Available to Everyone in Groups)

### `/id`
- **Function**: Shows the Telegram ID of the user who sent the command
- **Usage**: Just type `/id` in any group
- **Example Response**:
  ```
  👤 Your Telegram ID
  
  🆔 ID: 123456789
  👤 Name: John Doe
  📎 Username: @johndoe
  ```

### `/ids`
- **Function**: Shows the current group's Telegram ID
- **Usage**: Type `/ids` in any group
- **Example Response**:
  ```
  👥 Group Information
  
  🆔 Group ID: -1001234567890
  📝 Title: My Awesome Group
  📎 Username: @mygroup
  ```

### `/whois @username` or reply with `/whois`
- **Function**: Shows detailed info about a mentioned user or replied message author
- **Usage**: 
  - `@username /whois` or `/whois @username`
  - Reply to any message with `/whois`
- **Example Response**:
  ```
  👤 User Information
  
  🆔 ID: 987654321
  👤 Name: Jane Smith
  📎 Username: @janesmith
  🏷️ Status: 👤 Member
  ```

### `/mentionid @username` or reply with `/mentionid`
- **Function**: Creates a clickable mention using the user's Telegram ID
- **Usage**: Same as `/whois`
- **Example Response**:
  ```
  👤 Clickable mention: Jane Smith (clickable)
  🆔 User ID: 987654321
  ```

### `/help`
- **Function**: Shows group-specific help (different from private chat help)
- **Usage**: Type `/help` in any group
- **Features**: 
  - Shows user commands for everyone
  - Shows admin commands if you're a group admin

## 🛡️ Admin Commands (Only for Group Administrators)

### Warning System

#### `/warn @username [reason]` or reply with `/warn [reason]`
- **Function**: Issues a warning to a user
- **Usage**: 
  - `/warn @baduser Spamming the chat`
  - Reply to a message: `/warn Stop posting inappropriate content`
- **Features**:
  - Tracks warning count (max 3)
  - Stores reason and admin who issued warning
  - Cannot warn other admins

#### `/warnings @username` or reply with `/warnings`
- **Function**: Shows warning history for a user
- **Usage**: Same as `/warn`
- **Features**:
  - Shows total warning count
  - Displays last 5 warnings with dates and reasons
  - Shows clean record if no warnings

#### `/resetwarn @username` or reply with `/resetwarn`
- **Function**: Resets all warnings for a user
- **Usage**: Same as `/warn`
- **Features**: Clears warning history completely

### Mute System

#### `/mute @username [time]` or reply with `/mute [time]`
- **Function**: Mutes a user for specified duration
- **Usage**: 
  - `/mute @spammer 30m` (30 minutes)
  - `/mute @troublemaker 2h` (2 hours)
  - `/mute @baduser 1d` (1 day)
- **Time Formats**: `10m`, `2h`, `1d` (minutes, hours, days)
- **Default**: 1 hour if no time specified
- **Features**:
  - Removes all messaging permissions
  - Automatically expires after duration
  - Cannot mute admins

#### `/unmute @username` or reply with `/unmute`
- **Function**: Removes mute from a user
- **Usage**: Same as other user commands
- **Features**: Restores normal messaging permissions

### Kick/Ban System

#### `/kick @username` or reply with `/kick`
- **Function**: Kicks user from group (can rejoin)
- **Usage**: Same as other user commands
- **Features**: User can rejoin via invite link

#### `/ban @username` or reply with `/ban`
- **Function**: Permanently bans user from group
- **Usage**: Same as other user commands
- **Features**: User cannot rejoin until unbanned

#### `/unban @username` or reply with `/unban`
- **Function**: Unbans a previously banned user
- **Usage**: Same as other user commands
- **Features**: User can now rejoin the group

### Group Management

#### `/pin` (reply only)
- **Function**: Pins the replied message
- **Usage**: Reply to any message and type `/pin`
- **Features**: Pins message with notification

#### `/groupinfo`
- **Function**: Shows comprehensive group statistics
- **Usage**: Type `/groupinfo` in any group
- **Example Response**:
  ```
  📊 Group Information
  
  📝 Title: My Group
  🆔 ID: -1001234567890
  👥 Members: 1,234
  🛡️ Administrators: 5
  📅 Type: Supergroup
  
  📈 Moderation Stats:
  ⚠️ Total Warnings: 15
  👤 Users with Warnings: 8
  🔇 Active Mutes: 2
  📊 Total Moderated Users: 12
  ```

#### `/listadmins`
- **Function**: Lists all group administrators
- **Usage**: Type `/listadmins` in any group
- **Features**:
  - Shows creator separately
  - Lists all administrators with IDs
  - Identifies bots with 🤖 emoji

## 🔧 Technical Features

### Database System
- **File**: `group_data.json`
- **Structure**: Separate data per group ID
- **Features**:
  - Warning history with timestamps
  - Mute tracking with expiration
  - Group-specific settings
  - Automatic cleanup of expired mutes

### Permission System
- **Admin Check**: Verifies user is group administrator
- **Protection**: Cannot moderate other admins
- **Error Handling**: Graceful failure with helpful messages

### Smart User Detection
- **Username Support**: `@username` format
- **Reply Support**: Reply to any message
- **Flexible Input**: Works with or without @ symbol

## 🚀 Testing Guide

### 1. Add Bot to Test Group
1. Create a test group or use existing group
2. Add your bot to the group
3. Make sure bot has admin permissions for moderation commands

### 2. Test User Commands
```
/id - Should show your ID
/ids - Should show group ID
/whois @someone - Should show user info
/mentionid @someone - Should create clickable mention
/help - Should show group-specific help
```

### 3. Test Admin Commands (as group admin)
```
/warn @testuser Testing warning system
/warnings @testuser
/mute @testuser 5m
/unmute @testuser
/groupinfo
/listadmins
```

### 4. Test Reply Functionality
1. Reply to any user's message
2. Use commands like `/whois`, `/warn`, `/mute` etc.
3. Should work without mentioning username

## 🛠️ Troubleshooting

### Common Issues
1. **Commands not working**: Make sure bot is in a group, not private chat
2. **Admin commands failing**: Verify you're a group administrator
3. **Cannot moderate**: Check if target user is also an admin
4. **Database errors**: Check file permissions for `group_data.json`

### Error Messages
- `❌ This command is only available to group administrators.`
- `❌ Cannot warn/mute/kick group administrators.`
- `❌ Please reply to a user's message or mention a username.`

## 📊 Database Structure
```json
{
  "group_id": {
    "warnings": {
      "user_id": [
        {
          "reason": "Spam",
          "date": "2025-01-01T12:00:00",
          "admin_id": 123456789
        }
      ]
    },
    "mutes": {
      "user_id": {
        "until": "2025-01-01T13:00:00",
        "reason": "Muted for 1h",
        "admin_id": 123456789
      }
    },
    "settings": {
      "max_warnings": 3,
      "auto_action": "mute"
    }
  }
}
```

## 🎉 Ready to Use!
Your bot now has full group management capabilities! All commands are properly integrated and ready for production use.
