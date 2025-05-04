from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import and_, not_, or_
from app import db
from models import User, Gender, University, Like, Match, UserState
from config import STATES
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# State constants
PROFILE_MENU, EDIT_NAME, EDIT_AGE, EDIT_GENDER, EDIT_INTERESTED_IN, EDIT_UNIVERSITY, EDIT_BIO, EDIT_PHOTO, CONFIRM_DELETE = range(9)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Show the user's profile and offer options to edit or delete
    
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
            "✋ *Registration Required*\n\n"
            "To manage your UniMatch Ethiopia profile, "
            "please complete your registration first.\n\n"
            "Use /start to create your profile! 📝",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    # Show the user's profile
    await send_profile_summary(update, context, db_user)
    
    # Create an inline keyboard for profile management options
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit Name", callback_data="edit_name"),
            InlineKeyboardButton("🔢 Edit Age", callback_data="edit_age")
        ],
        [
            InlineKeyboardButton("⚧ Edit Gender", callback_data="edit_gender"),
            InlineKeyboardButton("💘 Edit Interest", callback_data="edit_interest")
        ],
        [
            InlineKeyboardButton("🏫 Edit University", callback_data="edit_uni"),
            InlineKeyboardButton("📝 Edit Bio", callback_data="edit_bio")
        ],
        [
            InlineKeyboardButton("🖼️ Change Photo", callback_data="edit_photo")
        ],
        [
            InlineKeyboardButton("❌ Delete Profile", callback_data="delete_profile")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
        ]
    ]
    
    await update.message.reply_text(
        "🔧 *UniMatch Ethiopia Profile Management*\n\n"
        "What would you like to do with your profile?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PROFILE_MENU

async def send_profile_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data) -> None:
    """
    Send a summary of the user's profile
    
    Args:
        update: The update object
        context: The context object
        user_data: The user data from the database
    """
    gender_display = "Male" if user_data.gender.name == "MALE" else "Female"
    interested_in_display = "Men" if user_data.interested_in.name == "MALE" else "Women"
    
    # Format the profile summary
    profile_text = (
        f"✨ *Your UniMatch Ethiopia Profile*\n\n"
        f"👤 *Name:* {user_data.full_name}\n"
        f"🔢 *Age:* {user_data.age}\n"
        f"⚧ *Gender:* {gender_display}\n"
        f"💘 *Interested in:* {interested_in_display}\n"
        f"🏫 *University:* {user_data.university.value}\n\n"
        f"📝 *Bio:*\n{user_data.bio or 'No bio provided.'}"
    )
    
    # Send the photo with the profile text
    if user_data.photo_id:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=user_data.photo_id,
            caption=profile_text,
            parse_mode="Markdown"
        )
    else:
        # If no photo, just send the text
        await update.message.reply_text(
            profile_text + "\n\n❗ *No profile photo uploaded.*",
            parse_mode="Markdown"
        )

async def profile_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle button clicks on the profile management menu
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    # Get the callback data
    data = query.data
    
    if data == "back_to_menu":
        await query.edit_message_text(
            "✅ *Returned to Main Menu*\n\n"
            "Use /help to see all available commands.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif data == "edit_name":
        await query.edit_message_text(
            "✏️ *Edit Your Name*\n\n"
            "Please enter your new full name:",
            parse_mode="Markdown"
        )
        return EDIT_NAME
    
    elif data == "edit_age":
        await query.edit_message_text(
            "🔢 *Edit Your Age*\n\n"
            "Please enter your new age (must be between 18-35):",
            parse_mode="Markdown"
        )
        return EDIT_AGE
    
    elif data == "edit_gender":
        keyboard = [
            [
                InlineKeyboardButton("👨 Male", callback_data="gender_male"),
                InlineKeyboardButton("👩 Female", callback_data="gender_female")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")
            ]
        ]
        
        await query.edit_message_text(
            "⚧ *Edit Your Gender*\n\n"
            "Please select your gender:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_GENDER
    
    elif data == "edit_interest":
        keyboard = [
            [
                InlineKeyboardButton("👨 Men", callback_data="interest_male"),
                InlineKeyboardButton("👩 Women", callback_data="interest_female")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")
            ]
        ]
        
        await query.edit_message_text(
            "💘 *Edit Your Interest*\n\n"
            "I'm interested in:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_INTERESTED_IN
    
    elif data == "edit_uni":
        # Create buttons for each university
        keyboard = []
        row = []
        
        # Get all university values (excluding ALL_UNIVERSITIES which is admin-only)
        for i, uni in enumerate([u for u in University if u.name != 'ALL_UNIVERSITIES']):
            # Create a new row every 2 buttons
            if i % 2 == 0 and i > 0:
                keyboard.append(row)
                row = []
            
            # Add the university button
            row.append(InlineKeyboardButton(
                uni.value[:20] + ('...' if len(uni.value) > 20 else ''), 
                callback_data=f"uni_{uni.name}")
            )
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
            
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")])
        
        await query.edit_message_text(
            "🏫 *Edit Your University*\n\n"
            "Please select your university:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_UNIVERSITY
    
    elif data == "edit_bio":
        await query.edit_message_text(
            "📝 *Edit Your Bio*\n\n"
            "Please enter a new bio (max 500 characters). Tell potential matches about yourself, "
            "your interests, and what you're looking for:",
            parse_mode="Markdown"
        )
        return EDIT_BIO
    
    elif data == "edit_photo":
        await query.edit_message_text(
            "🖼️ *Edit Your Profile Photo*\n\n"
            "Please send a new profile photo. Make sure it clearly shows your face. "
            "This helps other students recognize you.\n\n"
            "Send /cancel to keep your current photo.",
            parse_mode="Markdown"
        )
        return EDIT_PHOTO
    
    elif data == "delete_profile":
        await query.edit_message_text(
            "❌ *Delete Your Profile*\n\n"
            "⚠️ *WARNING:* This will permanently delete your UniMatch Ethiopia profile. "
            "All your matches, chats, and data will be lost.\n\n"
            "Are you sure you want to proceed?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yes, delete my profile", callback_data="confirm_delete")
                ],
                [
                    InlineKeyboardButton("🔙 No, keep my profile", callback_data="back_to_profile")
                ]
            ])
        )
        return CONFIRM_DELETE
    
    elif data == "back_to_profile":
        # Return to profile menu
        return await profile_command(update, context)
    
    else:
        # Handle unexpected callback data
        await query.edit_message_text(
            "⚠️ Unknown option. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Profile", callback_data="back_to_profile")]
            ])
        )
        return PROFILE_MENU

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new name entered by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    new_name = update.message.text.strip()
    
    # Validate the name
    if len(new_name) < 3 or len(new_name) > 100:
        await update.message.reply_text(
            "⚠️ Your name must be between 3 and 100 characters. Please try again."
        )
        return EDIT_NAME
    
    # Update the user's name in the database
    user = User.query.filter_by(telegram_id=update.effective_user.id).first()
    user.full_name = new_name
    db.session.commit()
    
    # Confirm the update
    await update.message.reply_text(
        f"✅ *Name Updated Successfully!*\n\n"
        f"Your name has been changed to: *{new_name}*",
        parse_mode="Markdown"
    )
    
    # Return to profile menu
    return await profile_command(update, context)

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new age entered by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    try:
        new_age = int(update.message.text.strip())
        
        # Validate the age
        if new_age < 18 or new_age > 35:
            await update.message.reply_text(
                "⚠️ Your age must be between 18 and 35. Please try again."
            )
            return EDIT_AGE
        
        # Update the user's age in the database
        user = User.query.filter_by(telegram_id=update.effective_user.id).first()
        user.age = new_age
        db.session.commit()
        
        # Confirm the update
        await update.message.reply_text(
            f"✅ *Age Updated Successfully!*\n\n"
            f"Your age has been changed to: *{new_age}*",
            parse_mode="Markdown"
        )
        
        # Return to profile menu
        return await profile_command(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number for your age."
        )
        return EDIT_AGE

async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new gender selected by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_profile":
        # Return to profile menu
        return await profile_command(update, context)
    
    # Update the user's gender in the database
    user = User.query.filter_by(telegram_id=update.effective_user.id).first()
    
    if data == "gender_male":
        user.gender = Gender.MALE
        gender_display = "Male"
    elif data == "gender_female":
        user.gender = Gender.FEMALE
        gender_display = "Female"
    else:
        # Invalid gender selection
        await query.edit_message_text(
            "⚠️ Invalid selection. Please try again."
        )
        return EDIT_GENDER
    
    db.session.commit()
    
    # Confirm the update
    await query.edit_message_text(
        f"✅ *Gender Updated Successfully!*\n\n"
        f"Your gender has been changed to: *{gender_display}*",
        parse_mode="Markdown"
    )
    
    # Return to profile menu
    return await profile_command(update, context)

async def edit_interested_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new interest selected by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_profile":
        # Return to profile menu
        return await profile_command(update, context)
    
    # Update the user's interest in the database
    user = User.query.filter_by(telegram_id=update.effective_user.id).first()
    
    if data == "interest_male":
        user.interested_in = Gender.MALE
        interest_display = "Men"
    elif data == "interest_female":
        user.interested_in = Gender.FEMALE
        interest_display = "Women"
    else:
        # Invalid interest selection
        await query.edit_message_text(
            "⚠️ Invalid selection. Please try again."
        )
        return EDIT_INTERESTED_IN
    
    db.session.commit()
    
    # Confirm the update
    await query.edit_message_text(
        f"✅ *Interest Updated Successfully!*\n\n"
        f"Your interest has been changed to: *{interest_display}*",
        parse_mode="Markdown"
    )
    
    # Return to profile menu
    return await profile_command(update, context)

async def edit_university(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new university selected by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_profile":
        # Return to profile menu
        return await profile_command(update, context)
    
    # Extract the university from the callback data
    uni_name = data.split('_')[1]
    
    try:
        # Get the University enum from the name
        university = University[uni_name]
        
        # Update the user's university in the database
        user = User.query.filter_by(telegram_id=update.effective_user.id).first()
        user.university = university
        db.session.commit()
        
        # Confirm the update
        await query.edit_message_text(
            f"✅ *University Updated Successfully!*\n\n"
            f"Your university has been changed to: *{university.value}*",
            parse_mode="Markdown"
        )
        
        # Return to profile menu
        return await profile_command(update, context)
        
    except (KeyError, ValueError):
        # Invalid university selection
        await query.edit_message_text(
            "⚠️ Invalid university selection. Please try again."
        )
        return EDIT_UNIVERSITY

async def edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new bio entered by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    new_bio = update.message.text.strip()
    
    # Validate the bio
    if len(new_bio) > 500:
        await update.message.reply_text(
            "⚠️ Your bio must be 500 characters or less. Please try again."
        )
        return EDIT_BIO
    
    # Update the user's bio in the database
    user = User.query.filter_by(telegram_id=update.effective_user.id).first()
    user.bio = new_bio
    db.session.commit()
    
    # Confirm the update
    await update.message.reply_text(
        f"✅ *Bio Updated Successfully!*\n\n"
        f"Your bio has been updated.",
        parse_mode="Markdown"
    )
    
    # Return to profile menu
    return await profile_command(update, context)

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the new photo sent by the user
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    # Check if this is a photo
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Please send a photo, not a text message or other file."
        )
        return EDIT_PHOTO
    
    # Get the largest photo (best quality)
    photo = update.message.photo[-1]
    photo_id = photo.file_id
    
    # Update the user's photo in the database
    user = User.query.filter_by(telegram_id=update.effective_user.id).first()
    user.photo_id = photo_id
    db.session.commit()
    
    # Confirm the update
    await update.message.reply_text(
        f"✅ *Photo Updated Successfully!*\n\n"
        f"Your profile photo has been updated.",
        parse_mode="Markdown"
    )
    
    # Return to profile menu
    return await profile_command(update, context)

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the confirmation for deleting the profile
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_profile":
        # User changed their mind, return to profile menu
        return await profile_command(update, context)
    
    elif data == "confirm_delete":
        # Get the user from the database
        user = User.query.filter_by(telegram_id=update.effective_user.id).first()
        
        if user:
            # Delete the user's data
            try:
                # Delete related data first (foreign key relationships)
                Like.query.filter_by(user_id=user.id).delete()
                Like.query.filter_by(liked_user_id=user.id).delete()
                
                # Delete matches involving this user
                matches_user1 = Match.query.filter_by(user1_id=user.id).all()
                matches_user2 = Match.query.filter_by(user2_id=user.id).all()
                
                for match in matches_user1 + matches_user2:
                    db.session.delete(match)
                
                # Delete the user's state
                UserState.query.filter_by(telegram_id=user.telegram_id).delete()
                
                # Finally delete the user
                db.session.delete(user)
                db.session.commit()
                
                await query.edit_message_text(
                    "✅ *Profile Deleted Successfully*\n\n"
                    "Your UniMatch Ethiopia profile and all associated data has been permanently deleted.\n\n"
                    "If you'd like to use UniMatch Ethiopia again in the future, "
                    "you can create a new profile with /start.",
                    parse_mode="Markdown"
                )
                
                # End the conversation
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error deleting user profile: {e}")
                db.session.rollback()
                
                await query.edit_message_text(
                    "❌ *Error Deleting Profile*\n\n"
                    "There was an error processing your request. Please try again later "
                    "or contact support for assistance.",
                    parse_mode="Markdown"
                )
                return ConversationHandler.END
        else:
            await query.edit_message_text(
                "❌ *Error Deleting Profile*\n\n"
                "Profile not found. It may have already been deleted.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    
    else:
        # Invalid selection
        await query.edit_message_text(
            "⚠️ Invalid selection. Please try again."
        )
        return CONFIRM_DELETE

async def cancel_profile_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel the profile editing process
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        ConversationHandler.END
    """
    await update.message.reply_text(
        "✅ *Profile Editing Cancelled*\n\n"
        "Your profile changes have been discarded.",
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END