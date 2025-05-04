from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app import db
from models import User, Like, Match
from config import ENABLE_NOTIFICATIONS
import logging
import random

# Initialize logger
logger = logging.getLogger(__name__)

# List of notification templates for likes
LIKE_NOTIFICATION_TEMPLATES = [
    "💕 Someone has shown interest in your UniMatch Ethiopia profile! Use /find to discover who it might be!",
    "❤️ You've got a secret admirer on UniMatch Ethiopia! Keep swiping to find out who!",
    "👀 Someone liked your profile on UniMatch Ethiopia! Continue matching to see if it's a connection!",
    "💘 Your UniMatch Ethiopia profile caught someone's eye! Keep using /find to discover potential matches!",
    "✨ Someone is interested in connecting with you on UniMatch Ethiopia! Keep exploring to see who!"
]

# List of notification templates for matches
MATCH_NOTIFICATION_TEMPLATES = [
    "🎉 *UniMatch Ethiopia Match Alert!* 🎉\n\nCongratulations! You matched with *{match_name}* from *{university}*!\n\nUse /chat to start your conversation now! 💬",
    "💘 *It's a Match on UniMatch Ethiopia!* 💘\n\nYou and *{match_name}* from *{university}* have liked each other!\n\nStart a conversation with /chat! 🗣️",
    "✨ *New UniMatch Ethiopia Connection!* ✨\n\nYou've matched with *{match_name}* from *{university}*!\n\nUse /chat to say hello! 👋",
    "🥂 *UniMatch Ethiopia Match Success!* 🥂\n\nYou and *{match_name}* from *{university}* are now connected!\n\nStart chatting with /chat! 💭",
    "💞 *New Match on UniMatch Ethiopia!* 💞\n\nCongratulations on matching with *{match_name}* from *{university}*!\n\nBegin your conversation with /chat! 📱"
]

async def send_like_notification(context: ContextTypes.DEFAULT_TYPE, liked_user_id: int) -> None:
    """
    Send a notification to a user when someone likes their profile,
    without revealing who liked them
    
    Args:
        context: The context object
        liked_user_id: The ID of the user who received the like
    """
    if not ENABLE_NOTIFICATIONS:
        return
    
    try:
        # Get the user who received the like
        liked_user = User.query.get(liked_user_id)
        
        if not liked_user:
            logger.warning(f"Cannot send like notification: User ID {liked_user_id} not found")
            return
        
        # Choose a random notification template
        notification_text = random.choice(LIKE_NOTIFICATION_TEMPLATES)
        
        # Create keyboard with find button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Find Matches", callback_data="find_matches")]
        ])
        
        # Send the notification
        await context.bot.send_message(
            chat_id=liked_user.telegram_id,
            text=notification_text,
            reply_markup=keyboard
        )
        
        logger.info(f"Sent like notification to user {liked_user_id}")
    
    except Exception as e:
        logger.error(f"Error sending like notification: {e}")

async def send_match_notification(context: ContextTypes.DEFAULT_TYPE, match_id: int, user1_id: int, user2_id: int) -> None:
    """
    Send a notification to both users when they match
    
    Args:
        context: The context object
        match_id: The ID of the match
        user1_id: The ID of the first user
        user2_id: The ID of the second user
    """
    if not ENABLE_NOTIFICATIONS:
        return
    
    try:
        # Get both users
        user1 = User.query.get(user1_id)
        user2 = User.query.get(user2_id)
        
        if not user1 or not user2:
            logger.warning(f"Cannot send match notification: One or both users not found")
            return
        
        # Choose a random notification template
        notification_template = random.choice(MATCH_NOTIFICATION_TEMPLATES)
        
        # Create keyboards with chat button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Start Chatting", callback_data=f"chat_with_{match_id}")]
        ])
        
        # Send notifications to both users
        # Notification for user1
        notification_text1 = notification_template.format(
            match_name=user2.full_name,
            university=user2.university.value
        )
        
        await context.bot.send_message(
            chat_id=user1.telegram_id,
            text=notification_text1,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Notification for user2
        notification_text2 = notification_template.format(
            match_name=user1.full_name,
            university=user1.university.value
        )
        
        await context.bot.send_message(
            chat_id=user2.telegram_id,
            text=notification_text2,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        logger.info(f"Sent match notifications to users {user1_id} and {user2_id}")
    
    except Exception as e:
        logger.error(f"Error sending match notification: {e}")

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Check if a user is a member of both required channels
    
    Args:
        context: The context object
        user_id: The telegram ID of the user to check
        
    Returns:
        True if the user is a member of both channels, False otherwise
    """
    from config import OFFICIAL_CHANNEL_ID, CONFESSION_CHANNEL_ID, REQUIRE_CHANNEL_MEMBERSHIP
    
    if not REQUIRE_CHANNEL_MEMBERSHIP:
        return True
    
    try:
        # Check official channel membership
        official_result = False
        if OFFICIAL_CHANNEL_ID:
            official_status = await context.bot.get_chat_member(
                chat_id=OFFICIAL_CHANNEL_ID,
                user_id=user_id
            )
            official_result = official_status.status in ['member', 'administrator', 'creator']
        else:
            # If no channel ID is set, consider it a success
            official_result = True
        
        # Check confession channel membership
        confession_result = False
        if CONFESSION_CHANNEL_ID:
            confession_status = await context.bot.get_chat_member(
                chat_id=CONFESSION_CHANNEL_ID,
                user_id=user_id
            )
            confession_result = confession_status.status in ['member', 'administrator', 'creator']
        else:
            # If no channel ID is set, consider it a success
            confession_result = True
        
        # User must be a member of both channels
        return official_result and confession_result
    
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        # In case of error, let the user proceed
        return True

async def prompt_channel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Prompt the user to join the required channels
    
    Args:
        update: The update object
        context: The context object
    """
    from config import OFFICIAL_CHANNEL_USERNAME, CONFESSION_CHANNEL_USERNAME
    
    # Create keyboard with channel links
    keyboard = []
    
    if OFFICIAL_CHANNEL_USERNAME:
        keyboard.append([
            InlineKeyboardButton(
                "🔗 Join Official Channel", 
                url=f"https://t.me/{OFFICIAL_CHANNEL_USERNAME}"
            )
        ])
    
    if CONFESSION_CHANNEL_USERNAME:
        keyboard.append([
            InlineKeyboardButton(
                "🔗 Join Confessions Channel", 
                url=f"https://t.me/{CONFESSION_CHANNEL_USERNAME}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ I've Joined Both", callback_data="check_membership")
    ])
    
    # Send the prompt
    await update.message.reply_text(
        "✋ *Channel Membership Required*\n\n"
        "To use UniMatch Ethiopia, you need to join our official channels:\n\n"
        "📢 *UniMatch Ethiopia* - For announcements and updates\n"
        "🔐 *UniMatch Confessions* - For anonymous confessions\n\n"
        "Please join both channels and then click the button below to continue.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_membership_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the membership check callback
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check if the user is a member of both channels
    is_member = await check_channel_membership(context, user_id)
    
    if is_member:
        await query.edit_message_text(
            "✅ *Channel Membership Verified*\n\n"
            "Thank you for joining our channels! You can now proceed with using UniMatch Ethiopia.\n\n"
            "Use /start to begin registration or access your profile.",
            parse_mode="Markdown"
        )
    else:
        # Re-create keyboard with channel links
        from config import OFFICIAL_CHANNEL_USERNAME, CONFESSION_CHANNEL_USERNAME
        
        keyboard = []
        
        if OFFICIAL_CHANNEL_USERNAME:
            keyboard.append([
                InlineKeyboardButton(
                    "🔗 Join Official Channel", 
                    url=f"https://t.me/{OFFICIAL_CHANNEL_USERNAME}"
                )
            ])
        
        if CONFESSION_CHANNEL_USERNAME:
            keyboard.append([
                InlineKeyboardButton(
                    "🔗 Join Confessions Channel", 
                    url=f"https://t.me/{CONFESSION_CHANNEL_USERNAME}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ I've Joined Both", callback_data="check_membership")
        ])
        
        # Send the prompt
        await query.edit_message_text(
            "❌ *Membership Verification Failed*\n\n"
            "You need to join both channels to use UniMatch Ethiopia.\n\n"
            "Please click the buttons below to join, then click 'I've Joined Both' to verify.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )