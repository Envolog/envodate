from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import and_, not_, or_
from app import db
from models import User, Like, Match, UserState
from bot.keyboards import profile_action_keyboard, next_profile_keyboard
from config import STATES
import logging
import random

# Initialize logger
logger = logging.getLogger(__name__)

async def find_matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start the process of finding matches
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is registered
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user or not db_user.registration_complete:
        await update.message.reply_text(
            "✋ *Registration Required*\n\n"
            "To start discovering UniMatch Ethiopia connections, "
            "please complete your profile first.\n\n"
            "Use /start to create your profile! 📝",
            parse_mode="Markdown"
        )
        return
    
    # Check if user is banned
    if db_user.is_banned:
        await update.message.reply_text(
            "❌ *Access Restricted*\n\n"
            "Sorry, your UniMatch Ethiopia account has been temporarily restricted "
            "from using the matching feature.\n\n"
            "For assistance, please contact support.",
            parse_mode="Markdown"
        )
        return
        
    # Send welcome message before showing profiles
    await update.message.reply_text(
        "🔍 *UniMatch Ethiopia Discovery*\n\n"
        f"Welcome to UniMatch discovery, {user.first_name}! "
        f"We're finding students from {db_user.university.value} who match your preferences.\n\n"
        "For each profile, you can like ❤️ or skip ⏭️. "
        "If someone likes you back, it's a match! 🎉",
        parse_mode="Markdown"
    )
    
    # Update user state
    db_user.current_state = STATES["VIEWING_PROFILE"]
    db.session.commit()
    
    # Update user state with proper error handling
    try:
        user_state = UserState.query.filter_by(telegram_id=user.id).first()
        if user_state:
            user_state.state = STATES["VIEWING_PROFILE"]
            db.session.commit()
        else:
            user_state = UserState(
                telegram_id=user.id,
                state=STATES["VIEWING_PROFILE"],
                data={}
            )
            db.session.add(user_state)
            db.session.commit()
    except Exception as e:
        # If there was an error (like unique violation), rollback and try updating
        db.session.rollback()
        logger.warning(f"Error managing user state: {e}")
        
        # Try again with just an update
        try:
            user_state = UserState.query.filter_by(telegram_id=user.id).first()
            if user_state:
                user_state.state = STATES["VIEWING_PROFILE"]
                db.session.commit()
                logger.info(f"Successfully updated user state after rollback for user {user.id}")
        except Exception as e2:
            logger.error(f"Fatal error managing user state: {e2}")
    
    await update.message.reply_text(
        "🔍 *Finding UniMatch Profiles*\n\n"
        "UniMatch Ethiopia is searching for your perfect connections...\n"
        "Use ❤️ to like someone or ⏭️ to view the next profile!",
        parse_mode="Markdown"
    )
    
    # Show the first potential match
    await show_next_profile(update, context, first_time=True)

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, first_time=False) -> None:
    """
    Show the next potential match profile
    
    Args:
        update: The update object
        context: The context object
        first_time: Whether this is the first profile being shown
    """
    if not first_time:
        query = update.callback_query
        await query.answer()
        user = query.from_user
    else:
        user = update.effective_user
    
    # Get the user from the database
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user:
        message = "You need to register first. Use /start to begin."
        if first_time:
            await update.message.reply_text(message)
        else:
            await query.edit_message_text(message)
        return
    
    # Find potential matches that:
    # 1. Match the user's gender preference
    # 2. Have the user's gender as their preference
    # 3. Match the university filter
    # 4. Have not been liked/disliked by the user
    # 5. Have registration complete
    # 6. Are not banned
    # 7. Have a profile photo
    
    # Get a list of user IDs that the current user has already interacted with
    interacted_users = [like.liked_user_id for like in db_user.likes_sent]
    
    potential_matches_query = User.query.filter(
        # Match gender preferences
        User.gender == db_user.interested_in,
        User.interested_in == db_user.gender,
        # University filter (if not "All Universities")
        ((User.university == db_user.university) | 
         (db_user.university.name == "ALL_UNIVERSITIES") |
         (User.university.name == "ALL_UNIVERSITIES")),
        # Not the current user
        User.id != db_user.id,
        # Not already interacted with
        ~User.id.in_(interacted_users),
        # Registration complete and not banned
        User.registration_complete == True,
        User.is_banned == False,
        # Has profile photo
        User.photo_id.isnot(None)
    )
    
    potential_matches = potential_matches_query.all()
    
    if not potential_matches:
        message = (
            "😔 *No UniMatch Profiles Available*\n\n"
            "UniMatch Ethiopia is still searching for your perfect match! "
            "The most compatible profiles from your university will appear here. "
            "Check back soon or try adjusting your preferences! 💫"
        )
        if first_time:
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await query.edit_message_text(message, parse_mode="Markdown")
        return
    
    # Pick a random match from the potential matches
    match = random.choice(potential_matches)
    
    # Display the match profile
    caption = (
        f"✨ *UniMatch Ethiopia Profile*\n\n"
        f"📋 *{match.full_name}*, {match.age}\n"
        f"🏫 {match.university.value}\n\n"
        f"{match.bio or 'No bio provided.'}\n\n"
        f"Do you want to connect with this student? Like ❤️ or Skip ⏭️"
    )
    
    # Create keyboard with like and skip buttons
    keyboard = profile_action_keyboard(match.id)
    
    if first_time:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=match.photo_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await query.edit_message_media(
            media={
                "type": "photo",
                "media": match.photo_id,
                "caption": caption,
                "parse_mode": "Markdown"
            },
            reply_markup=keyboard
        )

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a user liking a profile
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # like_<user_id>
    liked_user_id = int(data.split('_')[1])
    
    # Get the users from the database
    liker = User.query.filter_by(telegram_id=user.id).first()
    liked = User.query.get(liked_user_id)
    
    if not liker or not liked:
        await query.edit_message_text(
            "❌ *Profile Unavailable*\n\n"
            "UniMatch Ethiopia cannot find this profile. "
            "The user may have deactivated their account.\n\n"
            "Please try again with another profile.",
            parse_mode="Markdown"
        )
        return
    
    # Check if this is a duplicate like
    existing_like = Like.query.filter_by(
        user_id=liker.id,
        liked_user_id=liked.id
    ).first()
    
    if existing_like:
        # Update the existing like
        existing_like.is_like = True
        db.session.commit()
    else:
        # Record the like in the database
        like = Like(
            user_id=liker.id,
            liked_user_id=liked.id,
            is_like=True
        )
        db.session.add(like)
        db.session.commit()
        
        # Send a notification to the liked user (without revealing who liked them)
        from bot.notifications import send_like_notification
        await send_like_notification(context, liked.id)
    
    # Check if there's a mutual like
    mutual_like = Like.query.filter_by(
        user_id=liked.id,
        liked_user_id=liker.id,
        is_like=True
    ).first()
    
    if mutual_like:
        # Check if they're already matched
        existing_match = Match.query.filter(
            (
                (Match.user1_id == liker.id) & (Match.user2_id == liked.id)
            ) | (
                (Match.user1_id == liked.id) & (Match.user2_id == liker.id)
            )
        ).first()
        
        if not existing_match:
            # Create a match
            match = Match(
                user1_id=liker.id,
                user2_id=liked.id,
                is_active=True
            )
            db.session.add(match)
            db.session.commit()
            
            # Send match notifications to both users
            from bot.notifications import send_match_notification
            await send_match_notification(context, match.id, liker.id, liked.id)
        
        # Show a confirmation message
        match_text = f"✅ *Match Confirmed!* You liked {liked.full_name} and it's a match! 🎉\n\n"
        match_text += f"UniMatch Ethiopia has connected you! Use /chat to start your conversation."
        
        await query.edit_message_text(
            text=match_text,
            parse_mode="Markdown",
            reply_markup=next_profile_keyboard()
        )
    else:
        # Just show a confirmation message
        like_text = f"✅ *Like Sent!* You've shown interest in {liked.full_name}.\n\n"
        like_text += "UniMatch Ethiopia will notify you if they like you back! 💕"
        
        await query.edit_message_text(
            text=like_text,
            parse_mode="Markdown",
            reply_markup=next_profile_keyboard()
        )

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a user skipping a profile
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # skip_<user_id>
    skipped_user_id = int(data.split('_')[1])
    
    # Get the users from the database
    skipper = User.query.filter_by(telegram_id=user.id).first()
    skipped = User.query.get(skipped_user_id)
    
    if not skipper or not skipped:
        await query.edit_message_text(
            "❌ *Profile Unavailable*\n\n"
            "UniMatch Ethiopia cannot find this profile. "
            "The user may have deactivated their account.\n\n"
            "Please try again with another profile.",
            parse_mode="Markdown"
        )
        return
    
    # Check if this is a duplicate skip
    existing_like = Like.query.filter_by(
        user_id=skipper.id,
        liked_user_id=skipped.id
    ).first()
    
    if existing_like:
        # Update the existing record
        existing_like.is_like = False
        db.session.commit()
    else:
        # Record the skip in the database
        skip = Like(
            user_id=skipper.id,
            liked_user_id=skipped.id,
            is_like=False
        )
        db.session.add(skip)
        db.session.commit()
    
    # Show a confirmation message
    skip_text = f"❌ *Profile Skipped* - You passed on {skipped.full_name}.\n\n"
    skip_text += "UniMatch Ethiopia will continue finding your perfect match! 🔍"
    
    await query.edit_message_text(
        text=skip_text,
        parse_mode="Markdown",
        reply_markup=next_profile_keyboard()
    )

async def view_matched_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show the user their current matches
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is registered
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if not db_user or not db_user.registration_complete:
        await update.message.reply_text(
            "✋ *Registration Required*\n\n"
            "To view your UniMatch Ethiopia connections, "
            "please complete your profile first.\n\n"
            "Use /start to create your profile! 📝",
            parse_mode="Markdown"
        )
        return
    
    # Check if user is banned
    if db_user.is_banned:
        await update.message.reply_text(
            "❌ *Access Restricted*\n\n"
            "Sorry, your UniMatch Ethiopia account has been temporarily restricted "
            "from using the matching feature.\n\n"
            "For assistance, please contact support.",
            parse_mode="Markdown"
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
            "🔍 *No UniMatch Connections Yet*\n\n"
            "You haven't made any matches on UniMatch Ethiopia yet! "
            "Use /find to discover potential connections from your university. "
            "When someone likes you back, they'll appear here! ✨\n\n"
            "Keep exploring to find your perfect match!",
            parse_mode="Markdown"
        )
        return
    
    # Display each match
    for match in matches:
        # Determine which user is the match
        if match.user1_id == db_user.id:
            match_user = User.query.get(match.user2_id)
        else:
            match_user = User.query.get(match.user1_id)
        
        # Create a message with the match's details
        caption = (
            f"💘 *UniMatch Connection*\n\n"
            f"📋 *{match_user.full_name}*, {match_user.age}\n"
            f"🏫 {match_user.university.value}\n\n"
            f"{match_user.bio or 'No bio provided.'}\n\n"
            f"You've both matched! Start a conversation to discover your connection ✨"
        )
        
        # Create keyboard for chat actions
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Send Message", callback_data=f"send_msg_to_{match.id}"),
                InlineKeyboardButton("🚫 End Chat", callback_data=f"end_chat_{match.id}")
            ],
            [
                InlineKeyboardButton("⚠️ Report User", callback_data=f"report_user_{match_user.id}")
            ]
        ])
        
        await context.bot.send_photo(
            chat_id=user.id,
            photo=match_user.photo_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
