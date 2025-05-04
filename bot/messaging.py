from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import or_
from app import db
from models import User, Match, Message, UserState
from config import STATES
import logging

# Initialize logger
logger = logging.getLogger(__name__)

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show the user their active chats
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is registered
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user or not db_user.registration_complete:
        await update.message.reply_text(
            "You need to complete your registration first.\n"
            "Please use /start to register."
        )
        return
    
    # Check if user is banned
    if db_user.is_banned:
        await update.message.reply_text(
            "Sorry, you are currently banned from using the chat feature."
        )
        return
    
    # Get all active matches for the user
    matches = Match.query.filter(
        (
            (Match.user1_id == db_user.id) | 
            (Match.user2_id == db_user.id)
        ),
        Match.is_active == True
    ).all()
    
    if not matches:
        await update.message.reply_text(
            "You don't have any active matches to chat with.\n"
            "Use /find to start finding matches!"
        )
        return
    
    await update.message.reply_text(
        "Here are your active chats. Select one to start chatting!"
    )
    
    # Display each match
    for match in matches:
        # Determine which user is the match
        if match.user1_id == db_user.id:
            match_user = User.query.get(match.user2_id)
        else:
            match_user = User.query.get(match.user1_id)
        
        # Create a message with the match's details
        text = f"💬 Chat with *{match_user.full_name}*"
        
        # Create keyboard for chat actions
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Send Message", callback_data=f"send_msg_to_{match.id}")
            ]
        ])
        
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def send_message_to_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start a chat with a specific match
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # send_msg_to_<match_id>
    match_id = int(data.split('_')[-1])
    
    # Get the match from the database
    match = Match.query.get(match_id)
    if not match or not match.is_active:
        await query.edit_message_text(
            "This match is no longer active."
        )
        return
    
    # Get the user and match user
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user:
        await query.edit_message_text(
            "Error: Your user profile was not found."
        )
        return
    
    # Determine which user is the match
    if match.user1_id == db_user.id:
        match_user = User.query.get(match.user2_id)
    else:
        match_user = User.query.get(match.user1_id)
    
    if not match_user:
        await query.edit_message_text(
            "Error: Match user profile not found."
        )
        return
    
    # Set user state to chatting with this match
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["CHATTING"]
        user_state.data = {
            "match_id": match_id,
            "match_user_id": match_user.id
        }
        db.session.commit()
    else:
        user_state = UserState(
            telegram_id=user.id,
            state=STATES["CHATTING"],
            data={
                "match_id": match_id,
                "match_user_id": match_user.id
            }
        )
        db.session.add(user_state)
        db.session.commit()
    
    # Show chat history
    messages = Message.query.filter_by(match_id=match_id).order_by(Message.sent_at.asc()).all()
    
    # Display message history or a starter message
    if messages:
        chat_history = "📱 *Chat History*\n\n"
        for msg in messages:
            sender = User.query.get(msg.sender_id)
            chat_history += f"*{sender.full_name}*: {msg.content}\n\n"
        
        await context.bot.send_message(
            chat_id=user.id,
            text=chat_history,
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"Start chatting with *{match_user.full_name}*!\n"
                 f"Type a message below to send it.",
            parse_mode="Markdown"
        )
    
    # Show chat actions keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚫 End Chat", callback_data=f"end_chat_{match_id}"),
            InlineKeyboardButton("⚠️ Report User", callback_data=f"report_user_{match_user.id}")
        ]
    ])
    
    await context.bot.send_message(
        chat_id=user.id,
        text="You are now chatting. Type your message or use the buttons below.",
        reply_markup=keyboard
    )

async def process_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process a message sent by a user in chat mode
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    message_text = update.message.text
    
    # Get the user's state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    
    # If user is not in chatting state, ignore the message
    if not user_state or user_state.state != STATES["CHATTING"]:
        return
    
    # Get the match and user data
    match_id = user_state.data.get("match_id")
    match_user_id = user_state.data.get("match_user_id")
    
    if not match_id or not match_user_id:
        await update.message.reply_text(
            "Error: Chat data not found. Please use /chat to start chatting again."
        )
        return
    
    # Get the match and users from the database
    match = Match.query.get(match_id)
    db_user = User.query.filter_by(telegram_id=user.id).first()
    match_user = User.query.get(match_user_id)
    
    if not match or not match.is_active:
        await update.message.reply_text(
            "This chat has ended. Use /matches to see your active matches."
        )
        user_state.state = STATES["IDLE"]
        db.session.commit()
        return
    
    if not db_user or not match_user:
        await update.message.reply_text(
            "Error: User data not found. Please use /chat to start chatting again."
        )
        return
    
    # Store the message in the database
    message = Message(
        match_id=match_id,
        sender_id=db_user.id,
        receiver_id=match_user.id,
        content=message_text
    )
    db.session.add(message)
    db.session.commit()
    
    # Forward the message to the match user
    await context.bot.send_message(
        chat_id=match_user.telegram_id,
        text=f"💬 *{db_user.full_name}*: {message_text}",
        parse_mode="Markdown"
    )
    
    # Confirm to the sender
    await update.message.reply_text(
        "✅ Message sent!",
        reply_to_message_id=update.message.message_id
    )

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    End a chat with a match
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # end_chat_<match_id>
    match_id = int(data.split('_')[-1])
    
    # Get the match from the database
    match = Match.query.get(match_id)
    if not match:
        await query.edit_message_text(
            "Error: Match not found."
        )
        return
    
    # Get the user
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user:
        await query.edit_message_text(
            "Error: Your user profile was not found."
        )
        return
    
    # Determine which user is the match
    if match.user1_id == db_user.id:
        match_user = User.query.get(match.user2_id)
    else:
        match_user = User.query.get(match.user1_id)
    
    if not match_user:
        await query.edit_message_text(
            "Error: Match user profile not found."
        )
        return
    
    # End the match
    match.is_active = False
    from datetime import datetime
    match.ended_at = datetime.utcnow()
    db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state and user_state.state == STATES["CHATTING"]:
        user_state.state = STATES["IDLE"]
        db.session.commit()
    
    # Notify both users
    await query.edit_message_text(
        f"Chat with {match_user.full_name} has ended."
    )
    
    await context.bot.send_message(
        chat_id=match_user.telegram_id,
        text=f"{db_user.full_name} has ended the chat."
    )
