from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import UNIVERSITIES

def gender_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with gender options
    
    Returns:
        InlineKeyboardMarkup with gender buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("Male", callback_data="male"),
            InlineKeyboardButton("Female", callback_data="female")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def interested_in_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with interest options
    
    Returns:
        InlineKeyboardMarkup with interest buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("Male", callback_data="male"),
            InlineKeyboardButton("Female", callback_data="female")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def universities_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with university options
    
    Returns:
        InlineKeyboardMarkup with university buttons
    """
    keyboard = []
    row = []
    
    for i, university in enumerate(UNIVERSITIES):
        # Convert university name to enum-friendly format
        enum_name = university.upper().replace(" ", "_")
        if enum_name == "ALL_UNIVERSITIES":
            continue  # Add this at the end
        
        # Add 2 universities per row
        if i % 2 == 0 and i > 0:
            keyboard.append(row)
            row = []
        
        row.append(InlineKeyboardButton(university, callback_data=enum_name))
    
    # Add any remaining universities in the current row
    if row:
        keyboard.append(row)
    
    # Add "All Universities" as a separate row at the end
    keyboard.append([InlineKeyboardButton("All Universities", callback_data="ALL_UNIVERSITIES")])
    
    return InlineKeyboardMarkup(keyboard)

def confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard for profile confirmation
    
    Returns:
        InlineKeyboardMarkup with confirm/edit buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("✏️ Edit", callback_data="edit")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def profile_action_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Create a keyboard for profile actions (like/skip)
    
    Args:
        user_id: The ID of the user whose profile is being viewed
        
    Returns:
        InlineKeyboardMarkup with like/skip buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Like", callback_data=f"like_{user_id}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"skip_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def next_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard to show the next profile
    
    Returns:
        InlineKeyboardMarkup with next profile button
    """
    keyboard = [
        [InlineKeyboardButton("Next Profile ➡️", callback_data="next_profile")]
    ]
    return InlineKeyboardMarkup(keyboard)
