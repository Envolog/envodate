import random
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from app import db
from models import User, Gender, University, UserState
from bot.keyboards import (
    gender_keyboard, interested_in_keyboard,
    universities_keyboard, confirmation_keyboard
)
from config import REGISTRATION_STATES, REGISTRATION_STATE_IDS, STATES, STATE_IDS, MIN_AGE, MAX_AGE, UNIVERSITIES

# Initialize logger
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the registration process when the user sends /start
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    telegram_id = user.id
    
    # Check if user already exists and registration is complete
    existing_user = User.query.filter_by(telegram_id=telegram_id).first()
    
    if existing_user and existing_user.registration_complete:
        await update.message.reply_text(
            f"👋 *Welcome back to UniMatch Ethiopia, {existing_user.full_name}!* 👋\n\n"
            "Your profile is already set up and ready to go! Here's what you can do next:\n\n"
            "🔍 Use /find to discover new matches\n"
            "❤️ Use /matches to view your current matches\n"
            "🤫 Use /confess to share an anonymous confession in UniMatchConfessions\n"
            "❓ Use /help to see all available commands",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    # Check if the user is a member of required channels before registration
    from bot.notifications import check_channel_membership, prompt_channel_subscription
    from config import REQUIRE_CHANNEL_MEMBERSHIP
    
    if REQUIRE_CHANNEL_MEMBERSHIP:
        is_member = await check_channel_membership(context, telegram_id)
        if not is_member:
            # User needs to join the channels first
            await prompt_channel_subscription(update, context)
            # End the conversation and wait for callback_query
            return ConversationHandler.END
    
    # If user exists but registration is not complete, delete the user to start fresh
    if existing_user and not existing_user.registration_complete:
        db.session.delete(existing_user)
        db.session.commit()
    
    # Create a new user with minimal details
    new_user = User(
        telegram_id=telegram_id,
        full_name=user.full_name if user.full_name else "Unknown",
        age=0,
        gender=Gender.MALE,  # Default, will be updated
        interested_in=Gender.FEMALE,  # Default, will be updated
        university=University.ALL_UNIVERSITIES,  # Default, will be updated
        registration_complete=False,
        current_state=REGISTRATION_STATES["NAME"]
    )
    db.session.add(new_user)
    db.session.commit()
    
    # Store user state with error handling
    try:
        # First check if user state already exists
        existing_state = UserState.query.filter_by(telegram_id=telegram_id).first()
        
        if existing_state:
            # Update existing state
            existing_state.state = REGISTRATION_STATES["NAME"]
            existing_state.data = {}
            db.session.commit()
            logger.info(f"Updated existing user state for user {telegram_id}")
        else:
            # Create new state
            user_state = UserState(
                telegram_id=telegram_id,
                state=REGISTRATION_STATES["NAME"],
                data={}
            )
            db.session.add(user_state)
            db.session.commit()
            logger.info(f"Created new user state for user {telegram_id}")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Error managing user state during registration: {e}")
        
        # Try one more time just to update
        try:
            existing_state = UserState.query.filter_by(telegram_id=telegram_id).first()
            if existing_state:
                existing_state.state = REGISTRATION_STATES["NAME"]
                existing_state.data = {}
                db.session.commit()
                logger.info(f"Successfully updated user state after error for user {telegram_id}")
        except Exception as e2:
            logger.error(f"Fatal error managing user state during registration: {e2}")
    
    # Create welcome messages with emojis and vibrant text
    welcome_messages = [
        f"✨ *Hello {user.first_name}!* ✨\n\n"
        "💕 Welcome to *UniMatch Ethiopia* 💕\n\n"
        "I'm so excited to help you find your perfect match at your university! 💘\n"
        "Let's create your amazing profile together! You can cancel anytime by sending /cancel.\n\n"
        "🌟 First question: What's your full name? 🌟",
        
        f"🎉 *Hi there, {user.first_name}!* 🎉\n\n"
        "💖 Welcome to your love journey with *UniMatch Ethiopia* 💖\n\n"
        "Ready to meet amazing Ethiopian university students? Let's start by creating your stunning profile!\n"
        "You can always take a break by sending /cancel.\n\n"
        "👋 To begin: What's your full name?",
        
        f"💫 *Welcome aboard, {user.first_name}!* 💫\n\n"
        "❤️ You've just joined *UniMatch Ethiopia* - the premier dating community for Ethiopian university students! ❤️\n\n"
        "Your journey to finding love starts now! Creating a great profile is the first step.\n"
        "Feel free to pause anytime with /cancel.\n\n"
        "📝 Let's start with your full name:"
    ]
    
    # Choose a random welcome message
    welcome_message = random.choice(welcome_messages)
    
    try:
        await update.message.reply_text(
            welcome_message,
            parse_mode="Markdown"
        )
        logger.info(f"Sent welcome message to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            f"Hello {user.first_name}! Welcome to UniMatch Ethiopia.\n\n"
            "Let's create your profile. You can cancel anytime by sending /cancel.\n\n"
            "What is your full name?"
        )
    
    return REGISTRATION_STATE_IDS["NAME"]

async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's name and ask for age
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    full_name = update.message.text.strip()
    
    if len(full_name) < 3 or len(full_name) > 50:
        await update.message.reply_text(
            "Please enter a valid name (between 3 and 50 characters)."
        )
        return REGISTRATION_STATE_IDS["NAME"]
    
    # Update user name
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.full_name = full_name
        db_user.current_state = REGISTRATION_STATES["AGE"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATES["AGE"]
        user_state.data = {**user_state.data, "name": full_name}
        db.session.commit()
    
    # Create engaging name confirmation messages
    name_responses = [
        f"🤩 *Wonderful to meet you, {full_name}!* 🤩\n\n"
        f"🎂 How old are you? (Must be between {MIN_AGE} and {MAX_AGE}) 🎂",
        
        f"✨ *Fantastic name, {full_name}!* ✨\n\n"
        f"🎈 Next up: What's your age? (Between {MIN_AGE}-{MAX_AGE} please) 🎈",
        
        f"🌟 *{full_name}* - that's a lovely name! 🌟\n\n"
        f"⏳ Now, tell me your age (must be {MIN_AGE}-{MAX_AGE}) ⏳"
    ]
    
    name_response = random.choice(name_responses)
    
    try:
        await update.message.reply_text(
            name_response,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending name confirmation: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            f"Nice to meet you, {full_name}!\n\n"
            f"How old are you? (Must be between {MIN_AGE} and {MAX_AGE})"
        )
    
    return REGISTRATION_STATE_IDS["AGE"]

async def process_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's age and ask for gender
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    age_text = update.message.text.strip()
    
    try:
        age = int(age_text)
        if age < MIN_AGE or age > MAX_AGE:
            await update.message.reply_text(
                f"Sorry, this service is for users between {MIN_AGE} and {MAX_AGE} years old. "
                f"Please enter a valid age."
            )
            return REGISTRATION_STATE_IDS["AGE"]
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for your age."
        )
        return REGISTRATION_STATE_IDS["AGE"]
    
    # Update user age
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.age = age
        db_user.current_state = REGISTRATION_STATES["GENDER"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATES["GENDER"]
        user_state.data = {**user_state.data, "age": age}
        db.session.commit()
    
    # Create engaging gender selection messages
    gender_prompts = [
        f"🧩 *Perfect!* Now let's continue building your amazing profile.\n\n💁‍♂️💁‍♀️ *Please select your gender:*",
        f"🎯 *Age confirmed:* {age} years old!\n\n👤 *What's your gender?* Please choose below:",
        f"⭐ *Awesome!* You're {age}, great!\n\n🔍 *Tell me about yourself:* Select your gender:"
    ]
    
    gender_prompt = random.choice(gender_prompts)
    
    try:
        await update.message.reply_text(
            gender_prompt,
            parse_mode="Markdown",
            reply_markup=gender_keyboard()
        )
    except Exception as e:
        logger.error(f"Error sending gender selection prompt: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            "Please select your gender:",
            reply_markup=gender_keyboard()
        )
    
    return REGISTRATION_STATE_IDS["GENDER"]

async def process_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's gender and ask for interest
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    gender = query.data  # 'male' or 'female'
    
    # Update user gender
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.gender = Gender.MALE if gender == 'male' else Gender.FEMALE
        db_user.current_state = REGISTRATION_STATES["INTERESTED_IN"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATES["INTERESTED_IN"]
        user_state.data = {**user_state.data, "gender": gender}
        db.session.commit()
    
    # Create vibrant interest selection messages with emojis
    interest_prompts = [
        f"💯 *{gender.capitalize()} selected!* Great choice! 😊\n\n"
        f"💘 *Who are you interested in dating?* Choose below:",
        
        f"🌈 *Fantastic!* You identify as {gender.capitalize()}.\n\n"
        f"💕 *Now tell me:* Who makes your heart skip a beat?",
        
        f"👍 *Got it!* You're a {gender.capitalize()}.\n\n"
        f"❤️ *Let's find your match!* Who are you interested in?"
    ]
    
    interest_prompt = random.choice(interest_prompts)
    
    try:
        await query.edit_message_text(
            interest_prompt,
            parse_mode="Markdown",
            reply_markup=interested_in_keyboard()
        )
    except Exception as e:
        logger.error(f"Error sending interest selection prompt: {e}")
        # Fallback without markdown
        await query.edit_message_text(
            f"You selected: {gender.capitalize()}\n\n"
            "Who are you interested in dating?",
            reply_markup=interested_in_keyboard()
        )
    
    return REGISTRATION_STATE_IDS["INTERESTED_IN"]

async def process_interested_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's interest and ask for university
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    interested_in = query.data  # 'male' or 'female'
    
    # Update user interest
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.interested_in = Gender.MALE if interested_in == 'male' else Gender.FEMALE
        db_user.current_state = REGISTRATION_STATES["UNIVERSITY"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATES["UNIVERSITY"]
        user_state.data = {**user_state.data, "interested_in": interested_in}
        db.session.commit()
    
    # Create vibrant university selection messages with emojis
    university_prompts = [
        f"💝 *Perfect!* You're interested in {interested_in.capitalize()}. Great choice! 💯\n\n"
        f"🏫 *Which university do you attend?* 🎓\n"
        f"This helps us find matches at your campus!",
        
        f"💕 *Love is in the air!* You're looking for {interested_in.capitalize()}.\n\n"
        f"🏛️ *Now tell me:* Where do you study? 📚\n"
        f"Select your university below:",
        
        f"💘 *Wonderful!* Looking for {interested_in.capitalize()} matches.\n\n"
        f"🔍 *Let's narrow down your search:* 🌍\n"
        f"Which university are you from?"
    ]
    
    university_prompt = random.choice(university_prompts)
    
    try:
        await query.edit_message_text(
            university_prompt,
            parse_mode="Markdown",
            reply_markup=universities_keyboard()
        )
    except Exception as e:
        logger.error(f"Error sending university selection prompt: {e}")
        # Fallback without markdown
        await query.edit_message_text(
            f"You are interested in: {interested_in.capitalize()}\n\n"
            "Please select your university:",
            reply_markup=universities_keyboard()
        )
    
    return REGISTRATION_STATE_IDS["UNIVERSITY"]

async def process_university(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's university and ask for bio
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    university = query.data
    
    # Ensure the university is valid
    if university not in [u.name for u in University]:
        await query.edit_message_text(
            "Invalid university selection. Please try again.",
            reply_markup=universities_keyboard()
        )
        return REGISTRATION_STATE_IDS["UNIVERSITY"]
    
    # Update user university
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.university = getattr(University, university)
        db_user.current_state = REGISTRATION_STATES["BIO"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATES["BIO"]
        user_state.data = {**user_state.data, "university": university}
        db.session.commit()
    
    # Create engaging bio prompts with emojis
    bio_prompts = [
        f"🎓 *Awesome!* You're studying at {University[university].value}! 🏫\n\n"
        f"📝 *Let's add a personal touch!* Tell us a bit about yourself.\n"
        f"Share your interests, hobbies, or what you're looking for in a match.\n"
        f"(You can type 'skip' if you prefer to leave this blank for now)",
        
        f"🌟 *{University[university].value}* - excellent choice! 🌟\n\n"
        f"💬 *Time to express yourself!* Write a short bio to attract potential matches.\n"
        f"What makes you unique? What are you passionate about?\n"
        f"(Type 'skip' to continue without a bio)",
        
        f"🏛️ *{University[university].value}* - we have many students from there! 💯\n\n"
        f"✨ *Share your story!* A good bio increases your chances of finding matches.\n"
        f"What should potential matches know about you?\n"
        f"(Send 'skip' if you'd like to add this later)"
    ]
    
    bio_prompt = random.choice(bio_prompts)
    
    try:
        await query.edit_message_text(
            bio_prompt,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending bio prompt: {e}")
        # Fallback without markdown
        await query.edit_message_text(
            f"University: {University[university].value}\n\n"
            "Please enter a short bio about yourself (optional). "
            "You can skip this by typing 'skip'."
        )
    
    return REGISTRATION_STATE_IDS["BIO"]

async def process_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's bio and ask for photo
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    bio = update.message.text.strip()
    
    # Skip bio if requested
    if bio.lower() == 'skip':
        bio = ""
    
    # Limit bio length
    if len(bio) > 300:
        await update.message.reply_text(
            "Your bio is too long. Please keep it under 300 characters."
        )
        return REGISTRATION_STATE_IDS["BIO"]
    
    # Update user bio
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.bio = bio
        db_user.current_state = REGISTRATION_STATE_IDS["PHOTO"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATE_IDS["PHOTO"]
        user_state.data = {**user_state.data, "bio": bio}
        db.session.commit()
    
    # Create engaging photo request messages with emojis
    photo_prompts = [
        f"💯 *Bio saved successfully!* Now for the fun part! 📸\n\n"
        f"🤳 *Please send your best profile photo!*\n"
        f"Your photo is crucial for matching with others.\n"
        f"Choose a clear photo where your face is visible!",
        
        f"✨ *Perfect bio!* Time to add a face to your amazing profile! 🌟\n\n"
        f"📷 *Send me a great photo of yourself*\n"
        f"This is required for matching and helps others connect with you!\n"
        f"Choose a photo that shows your best side! 😊",
        
        f"🎯 *Bio received!* Now let's make your profile shine! ✨\n\n"
        f"📱 *Your profile photo is essential!*\n"
        f"Send a clear, recent photo of yourself.\n"
        f"This will greatly increase your chances of finding matches! 💘"
    ]
    
    photo_prompt = random.choice(photo_prompts)
    
    try:
        await update.message.reply_text(
            photo_prompt,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending photo prompt: {e}")
        # Fallback without markdown
        await update.message.reply_text(
            "Great! Now, please send me a profile photo. "
            "This is required for matching. "
            "Make sure it's a clear photo of yourself."
        )
    
    return REGISTRATION_STATE_IDS["PHOTO"]

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, is_text=False) -> int:
    """
    Process the user's photo and ask for confirmation
    
    Args:
        update: The update object
        context: The context object
        is_text: Whether this is a text message instead of a photo
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    
    # Check if user sent text instead of photo
    if is_text:
        await update.message.reply_text(
            "Please send a photo, not text. "
            "A profile photo is required for matching."
        )
        return REGISTRATION_STATE_IDS["PHOTO"]
    
    # Get the photo
    photo = update.message.photo[-1]  # Get the largest size
    photo_id = photo.file_id
    
    # Update user photo
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.photo_id = photo_id
        db_user.current_state = REGISTRATION_STATE_IDS["CONFIRM"]
        db.session.commit()
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = REGISTRATION_STATE_IDS["CONFIRM"]
        user_state.data = {**user_state.data, "photo_id": photo_id}
        db.session.commit()
    
    # Send profile summary for confirmation
    await send_profile_summary(update, context, db_user)
    
    return REGISTRATION_STATE_IDS["CONFIRM"]

async def send_profile_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data):
    """
    Send a summary of the user's profile for confirmation
    
    Args:
        update: The update object
        context: The context object
        user_data: The user data from the database
    """
    gender_text = "Male" if user_data.gender == Gender.MALE else "Female"
    interested_in_text = "Male" if user_data.interested_in == Gender.MALE else "Female"
    
    # Send the profile photo with the summary
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=user_data.photo_id,
        caption=(
            "📝 *Your Profile Summary:*\n\n"
            f"*Name:* {user_data.full_name}\n"
            f"*Age:* {user_data.age}\n"
            f"*Gender:* {gender_text}\n"
            f"*Interested In:* {interested_in_text}\n"
            f"*University:* {user_data.university.value}\n"
            f"*Bio:* {user_data.bio or 'Not provided'}\n\n"
            "Is this information correct? You can confirm or edit your profile."
        ),
        parse_mode="Markdown",
        reply_markup=confirmation_keyboard()
    )

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the user's confirmation and complete registration
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    choice = query.data  # 'confirm' or 'edit'
    
    if choice == 'edit':
        # Reset to the beginning of registration
        await query.edit_message_text(
            "Let's edit your profile. What is your full name?"
        )
        
        # Update user state
        db_user = User.query.filter_by(telegram_id=user.id).first()
        if db_user:
            db_user.current_state = REGISTRATION_STATE_IDS["NAME"]
            db.session.commit()
            
        user_state = UserState.query.filter_by(telegram_id=user.id).first()
        if user_state:
            user_state.state = REGISTRATION_STATE_IDS["NAME"]
            db.session.commit()
            
        return REGISTRATION_STATE_IDS["NAME"]
    
    # Confirm and complete registration
    db_user = User.query.filter_by(telegram_id=user.id).first()
    if db_user:
        db_user.registration_complete = True
        db_user.current_state = STATES["IDLE"]
        db.session.commit()
        
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["IDLE"]
        db.session.commit()
    
    await query.edit_message_text(
        "🎉 *Congratulations!* Your UniMatch Ethiopia profile is complete! 🎉\n\n"
        "You're now part of the largest dating community for Ethiopian university students!\n\n"
        "What would you like to do next?\n\n"
        "🔍 Use /find to start discovering matches\n"
        "❤️ Use /matches to see your current matches\n"
        "🤫 Use /confess to share an anonymous confession in UniMatchConfessions\n"
        "❓ Use /help to see all available commands",
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END

async def register_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generic handler for buttons that aren't handled by specific handlers
    
    Args:
        update: The update object
        context: The context object
    """
    query = update.callback_query
    await query.answer()
    
    # Log the unhandled button press
    logger.warning(f"Unhandled button press: {query.data}")
    
    # Let the user know we received their input
    await query.edit_message_text(
        "Sorry, this action is not available at the moment."
    )
