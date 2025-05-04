import re
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from app import db
from models import User, Confession, BannedWord, UserState
from config import STATES, CONFESSION_CHANNEL_ID, REQUIRE_CONFESSION_APPROVAL
import logging

# Initialize logger
logger = logging.getLogger(__name__)

async def confess_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Start the confession submission process
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    
    # Check if user is registered
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user or not db_user.registration_complete:
        await update.message.reply_text(
            "You need to complete your registration first.\n"
            "Please use /start to register."
        )
        return ConversationHandler.END
    
    # Check if user is banned
    if db_user.is_banned:
        await update.message.reply_text(
            "Sorry, you are currently banned from submitting confessions."
        )
        return ConversationHandler.END
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["CONFESSION"]
        db.session.commit()
    else:
        user_state = UserState(
            telegram_id=user.id,
            state=STATES["CONFESSION"],
            data={}
        )
        db.session.add(user_state)
        db.session.commit()
    
    await update.message.reply_text(
        "💌 *UniMatchConfessions*\n\n"
        "Your confession will be posted anonymously to the UniMatchConfessions channel. "
        "Please type your confession below. It should be respectful and "
        "not contain offensive content.\n\n"
        "Type /cancel to cancel the submission.",
        parse_mode="Markdown"
    )
    
    return "confession_text"

async def process_confession_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the confession text submitted by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    confession_text = update.message.text.strip()
    
    # Check if the confession is too short or too long
    if len(confession_text) < 10:
        await update.message.reply_text(
            "Your confession is too short. Please provide a more detailed confession."
        )
        return "confession_text"
    
    if len(confession_text) > 500:
        await update.message.reply_text(
            "Your confession is too long. Please limit it to 500 characters."
        )
        return "confession_text"
    
    # Get the user from the database
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user:
        await update.message.reply_text(
            "Error: Your user profile was not found. Please use /start to register."
        )
        return ConversationHandler.END
    
    # Filter offensive words
    filtered_text = await filter_offensive_words(confession_text)
    
    # Create the confession in the database
    confession = Confession(
        user_id=db_user.id,
        content=filtered_text,
        is_approved=not REQUIRE_CONFESSION_APPROVAL  # Auto-approve if not requiring approval
    )
    db.session.add(confession)
    db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["IDLE"]
        db.session.commit()
    
    # Post to channel if auto-approved
    if not REQUIRE_CONFESSION_APPROVAL:
        await post_confession_to_channel(context, confession)
        await update.message.reply_text(
            "✅ *Success!* Your confession has been posted anonymously to the UniMatchConfessions channel.\n"
            "Thank you for sharing your thoughts with the Ethiopian university community! 💭",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "✅ *Received!* Your confession has been submitted for approval.\n"
            "It will be posted to the UniMatchConfessions channel once reviewed by our team.\n"
            "Thank you for sharing your thoughts with the Ethiopian university community! 💭",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END

async def filter_offensive_words(text: str) -> str:
    """
    Filter offensive words from the confession text
    
    Args:
        text: The confession text
        
    Returns:
        The filtered text
    """
    # Get banned words from the database
    banned_words = BannedWord.query.all()
    
    # If no banned words in DB, use the default list
    if not banned_words:
        from config import DEFAULT_BANNED_WORDS
        banned_words_list = DEFAULT_BANNED_WORDS
    else:
        banned_words_list = [word.word for word in banned_words]
    
    # Replace offensive words with asterisks
    filtered_text = text
    for word in banned_words_list:
        # Use word boundaries to match whole words only
        pattern = r'\b' + re.escape(word) + r'\b'
        replacement = '*' * len(word)
        filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
    
    return filtered_text

async def post_confession_to_channel(context: ContextTypes.DEFAULT_TYPE, confession: Confession) -> None:
    """
    Post a confession to the channel
    
    Args:
        context: The context object
        confession: The confession to post
    """
    if not CONFESSION_CHANNEL_ID:
        logger.error("CONFESSION_CHANNEL_ID not set, cannot post confession")
        return
    
    try:
        message = await context.bot.send_message(
            chat_id=CONFESSION_CHANNEL_ID,
            text=f"💌 *UniMatchConfessions #{confession.id}*\n\n{confession.content}\n\n"
                 f"🎓 _Share your own thoughts anonymously through the @UniMatch_Ethiopia bot_",
            parse_mode="Markdown"
        )
        
        # Update confession with message ID
        confession.is_posted = True
        confession.channel_message_id = message.message_id
        db.session.commit()
        
        logger.info(f"Posted confession #{confession.id} to channel")
    except Exception as e:
        logger.error(f"Failed to post confession to channel: {e}")

async def handle_confession(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin function to approve or reject a confession
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # format: approve_confession_<id> or reject_confession_<id>
    
    # Check if user is an admin
    from bot.admin import is_admin
    if not await is_admin(user.id):
        await query.edit_message_text(
            "You do not have permission to perform this action."
        )
        return
    
    action, _, confession_id = data.split('_', 2)
    confession_id = int(confession_id)
    
    # Get the confession from the database
    confession = Confession.query.get(confession_id)
    if not confession:
        await query.edit_message_text(
            "Error: Confession not found."
        )
        return
    
    if action == "approve":
        confession.is_approved = True
        db.session.commit()
        
        # Post to channel
        await post_confession_to_channel(context, confession)
        
        await query.edit_message_text(
            f"✅ Confession #{confession_id} approved and posted to UniMatchConfessions channel.\n\n"
            f"Thank you for helping maintain a positive community experience!"
        )
    else:  # reject
        db.session.delete(confession)
        db.session.commit()
        
        await query.edit_message_text(
            f"❌ Confession #{confession_id} rejected and deleted.\n\n"
            f"Thank you for helping maintain a positive community experience!"
        )
