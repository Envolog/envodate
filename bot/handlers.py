from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ConversationHandler, ContextTypes
)
import logging

# Import handlers from other modules
from bot.registration import (
    start_command, process_name, process_age, process_gender,
    process_interested_in, process_university, process_bio,
    process_photo, confirm_registration, register_button_handler
)
from bot.matching import (
    find_matches_command, handle_like, handle_skip,
    show_next_profile, view_matched_profiles
)
from bot.messaging import (
    chat_command, process_chat_message, end_chat,
    send_message_to_match
)
from bot.confessions import (
    confess_command, process_confession_text,
    handle_confession
)
from bot.admin import (
    admin_command, view_reports, view_banned_users,
    ban_user, unban_user, handle_report,
    process_report_reason
)
from bot.profile import (
    profile_command, profile_button_handler, edit_name,
    edit_age, edit_gender, edit_interested_in, edit_university,
    edit_bio, edit_photo, confirm_delete, cancel_profile_edit
)
from bot.notifications import (
    handle_membership_check
)
from bot.utils import cancel_command, help_command, about_command, ping_command

# Initialize logger
logger = logging.getLogger(__name__)

def register_handlers(application: Application) -> None:
    """
    Register all command and message handlers with the application
    
    Args:
        application: The bot application instance
    """
    logger.info("Registering handlers...")
    
    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            'reg_name': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)],
            'reg_age': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_age)],
            'reg_gender': [CallbackQueryHandler(process_gender, pattern='^(male|female)$')],
            'reg_interested_in': [CallbackQueryHandler(process_interested_in, pattern='^(male|female)$')],
            'reg_university': [CallbackQueryHandler(process_university)],
            'reg_bio': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_bio)],
            'reg_photo': [
                MessageHandler(filters.PHOTO, process_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: process_photo(update, context, is_text=True))
            ],
            'reg_confirm': [CallbackQueryHandler(confirm_registration, pattern='^(confirm|edit)$')],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        name="registration",
        persistent=False
    )
    application.add_handler(registration_handler)
    
    # Matching handlers
    application.add_handler(CommandHandler('find', find_matches_command))
    application.add_handler(CallbackQueryHandler(handle_like, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(handle_skip, pattern='^skip_'))
    application.add_handler(CallbackQueryHandler(show_next_profile, pattern='^next_profile$'))
    application.add_handler(CommandHandler('matches', view_matched_profiles))
    
    # Chat handlers
    application.add_handler(CommandHandler('chat', chat_command))
    application.add_handler(CallbackQueryHandler(send_message_to_match, pattern='^send_msg_to_'))
    application.add_handler(CallbackQueryHandler(end_chat, pattern='^end_chat_'))
    application.add_handler(CallbackQueryHandler(handle_report, pattern='^report_user_'))
    
    # Confession handlers
    confession_handler = ConversationHandler(
        entry_points=[CommandHandler('confess', confess_command)],
        states={
            'confession_text': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_confession_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        name="confession",
        persistent=False
    )
    application.add_handler(confession_handler)
    
    # Report handlers
    report_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_report, pattern='^report_user_')],
        states={
            'report_reason': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_reason)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        name="report",
        persistent=False
    )
    application.add_handler(report_handler)
    
    # Admin handlers
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('reports', view_reports))
    application.add_handler(CommandHandler('banned', view_banned_users))
    application.add_handler(CommandHandler('ban', ban_user))
    application.add_handler(CommandHandler('unban', unban_user))
    
    # Profile management handlers
    profile_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', profile_command)],
        states={
            0: [CallbackQueryHandler(profile_button_handler)],  # PROFILE_MENU
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],  # EDIT_NAME
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],  # EDIT_AGE
            3: [CallbackQueryHandler(edit_gender)],  # EDIT_GENDER
            4: [CallbackQueryHandler(edit_interested_in)],  # EDIT_INTERESTED_IN
            5: [CallbackQueryHandler(edit_university)],  # EDIT_UNIVERSITY
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_bio)],  # EDIT_BIO
            7: [MessageHandler(filters.PHOTO, edit_photo)],  # EDIT_PHOTO
            8: [CallbackQueryHandler(confirm_delete)],  # CONFIRM_DELETE
        },
        fallbacks=[CommandHandler('cancel', cancel_profile_edit)],
        name="profile_management",
        persistent=False
    )
    application.add_handler(profile_handler)
    
    # Channel membership handlers
    application.add_handler(CallbackQueryHandler(handle_membership_check, pattern='^check_membership$'))
    application.add_handler(CallbackQueryHandler(handle_membership_check, pattern='^find_matches$'))
    
    # Help and About commands
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('about', about_command))
    
    # Ping command for testing
    application.add_handler(CommandHandler('ping', ping_command))
    
    # Generic button handler
    application.add_handler(CallbackQueryHandler(register_button_handler))
    
    # Handle chat messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        process_chat_message
    ))
    
    logger.info("All handlers registered successfully")
