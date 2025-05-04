from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from app import db
from models import UserState
from config import STATES
import logging

# Initialize logger
logger = logging.getLogger(__name__)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Simple ping command to test if the bot is responding
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    logger.info(f"Received ping from user {user.id}")
    
    responses = [
        f"🏓 *Pong!* Hi {user.first_name}! UniMatch Ethiopia is alive and ready to help you find love! ❤️",
        f"✨ *I'm here, {user.first_name}!* UniMatch Ethiopia is ready to connect you with your perfect match! 💘",
        f"🚀 *UniMatch Ethiopia is online!* Hey {user.first_name}, looking for love today? We're here to help! 💫",
        f"🌟 *Connection successful!* {user.first_name}, your UniMatch Ethiopia dating adventure awaits! 💕",
        f"🎯 *Ping received!* Ready to find your match at your university, {user.first_name}? Let's go! 🥰"
    ]
    
    import random
    response = random.choice(responses)
    
    try:
        await update.message.reply_text(
            response,
            parse_mode="Markdown"
        )
        logger.info(f"Successfully sent ping response to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending ping response: {e}")
        # Fallback without markdown
        await update.message.reply_text(f"Pong! Hi {user.first_name}! The bot is working! ✅")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the current conversation and reset user state
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        ConversationHandler.END
    """
    user = update.effective_user
    
    # Reset user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["IDLE"]
        user_state.data = {}
        db.session.commit()
    
    cancel_messages = [
        "✅ *Operation cancelled!* What adventure shall we embark on next? 🚀",
        "🔄 *All cleared!* Ready for a new beginning? What's on your mind? 🌈",
        "🎮 *Reset successful!* Where to next on your dating journey? 💫",
        "🌟 *Fresh start!* What would you like to explore now? 🧭",
        "✨ *Command cancelled!* Your wish is my command - what's next? 🪄"
    ]
    
    import random
    cancel_response = random.choice(cancel_messages)
    
    try:
        await update.message.reply_text(
            cancel_response,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending cancel response: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            "✅ Operation cancelled! What would you like to do next?"
        )
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show help information
    
    Args:
        update: The update object
        context: The context object
    """
    help_text = (
        "💖 *UniMatch Ethiopia Help Center* 💖\n\n"
        "*Magical Commands:*\n"
        "🔐 /start - Create your perfect profile\n"
        "👤 /profile - Manage, edit or delete your profile\n"
        "❤️ /find - Discover your potential soulmate\n"
        "💑 /matches - See who matched with you\n"
        "💌 /chat - Send sweet messages to your matches\n"
        "🎭 /confess - Share anonymous thoughts in UniMatchConfessions\n"
        "ℹ️ /about - Learn about UniMatch Ethiopia\n"
        "🚫 /cancel - Stop current action instantly\n"
        "🏓 /ping - Check if I'm awake and ready\n"
        "🔍 /help - Show this helpful guide\n\n"
        
        "*Why Choose UniMatch Ethiopia?* ✨\n"
        "We're your dedicated matchmaker for Ethiopian university students! "
        "Our mission is to help you find genuine connections in a fun, "
        "safe, and private environment. Your dating journey starts here! 🚀\n\n"
        
        "*Amazing Features:* 🌟\n"
        "💎 Beautiful profile creation\n"
        "🛡️ Privacy-focused matching\n"
        "📱 Smooth in-bot messaging\n"
        "🤫 Exciting anonymous confessions in UniMatchConfessions\n"
        "🏫 Smart university filtering\n\n"
        
        "*Need a Helping Hand?* 🤗\n"
        "If you have questions or need assistance,\n"
        "don't hesitate to reach out to our friendly admins!"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show information about the bot and its developer
    
    Args:
        update: The update object
        context: The context object
    """
    about_text = (
        "✨ *About UniMatch Ethiopia* ✨\n\n"
        "🔢 *Version:* 1.0\n"
        "👨‍💻 *Created by:* @envologia\n"
        "🗓️ *Released:* May 2025\n\n"
        
        "💝 *Our Love Mission:*\n"
        "UniMatch Ethiopia is on a mission to create meaningful connections between university "
        "students across Ethiopia! Our magical matching algorithm finds your "
        "perfect match based on preferences, interests, and university. "
        "Your journey to finding love starts with a simple hello! 💫\n\n"
        
        "🌟 *Awesome Features:*\n"
        "💯 Smart university-specific matching\n"
        "💌 Secure private messaging\n"
        "🎭 Fun anonymous confessions in UniMatchConfessions channel\n"
        "🔄 Complete profile management\n"
        "🔔 Exciting match notifications\n"
        "🔒 Strong privacy protections\n"
        "🛡️ Reliable moderation system\n\n"
        
        "🏫 *Universities We Connect:*\n"
        "🎓 Addis Ababa University\n"
        "🎓 Bahir Dar University\n"
        "🎓 Hawassa University\n"
        "🎓 Jimma University\n"
        "🎓 Mekelle University\n"
        "🎓 Gondar University\n"
        "🎓 Adama Science and Technology University\n"
        "🎓 Haramaya University\n"
        "🎓 Arba Minch University\n"
        "🎓 Dire Dawa University\n\n"
        
        "📞 *Let's Talk!*\n"
        "Questions? Ideas? Just want to say hi? Contact the UniMatch Ethiopia team "
        "through @envologia on Telegram! We love hearing from you! 💕"
    )
    
    # Create buttons with colorful actions
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Developer", url="https://t.me/envologia")],
        [InlineKeyboardButton("💌 Join Our Community", url="https://t.me/UniMatch_Ethiopia")],
        [InlineKeyboardButton("❤️ Share with Friends", url="https://t.me/share/url?url=https://t.me/UniMatch_Ethiopia&text=Join%20me%20on%20UniMatch%20Ethiopia%20-%20the%20ultimate%20dating%20platform%20for%20Ethiopian%20university%20students!")]
    ])
    
    await update.message.reply_text(
        about_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
