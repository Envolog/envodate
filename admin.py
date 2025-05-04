from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import desc
from app import db
from models import User, Report, Match, UserState, Confession
from config import ADMIN_IDS, STATES, STATE_IDS
import logging
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)

async def is_admin(telegram_id: int) -> bool:
    """
    Check if a user is an admin
    
    Args:
        telegram_id: The Telegram ID of the user
        
    Returns:
        True if the user is an admin, False otherwise
    """
    return telegram_id in ADMIN_IDS

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show admin commands
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to use admin commands."
        )
        return
    
    await update.message.reply_text(
        "🛡️ *UniMatch Ethiopia Admin Panel*\n\n"
        "*Available Commands:*\n"
        "/reports - View recent user reports\n"
        "/banned - View banned users\n"
        "/ban <user_id> - Ban a user\n"
        "/unban <user_id> - Unban a user\n"
        "/approve_confessions - Review pending UniMatchConfessions\n\n"
        "_Thank you for helping maintain a safe environment for Ethiopian university students!_",
        parse_mode="Markdown"
    )

async def view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show recent user reports
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to view reports."
        )
        return
    
    # Get recent reports
    reports = Report.query.filter_by(is_resolved=False).order_by(desc(Report.created_at)).limit(10).all()
    
    if not reports:
        await update.message.reply_text(
            "No unresolved reports found."
        )
        return
    
    # Display each report
    for report in reports:
        reporter = User.query.get(report.reporter_id)
        reported = User.query.get(report.reported_user_id)
        
        if not reporter or not reported:
            continue
        
        report_text = (
            f"📝 *Report #{report.id}*\n\n"
            f"*Reporter:* {reporter.full_name} (ID: {reporter.id})\n"
            f"*Reported User:* {reported.full_name} (ID: {reported.id})\n"
            f"*Reason:* {report.reason}\n"
            f"*Date:* {report.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Create keyboard for admin actions
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Ban User", callback_data=f"admin_ban_{reported.id}"),
                InlineKeyboardButton("Dismiss Report", callback_data=f"dismiss_report_{report.id}")
            ]
        ])
        
        await context.bot.send_message(
            chat_id=user.id,
            text=report_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def view_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show banned users
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to view banned users."
        )
        return
    
    # Get banned users
    banned_users = User.query.filter_by(is_banned=True).all()
    
    if not banned_users:
        await update.message.reply_text(
            "No banned users found."
        )
        return
    
    # Display banned users
    banned_text = "🚫 *Banned Users:*\n\n"
    for banned_user in banned_users:
        banned_text += f"- {banned_user.full_name} (ID: {banned_user.id}, TG: {banned_user.telegram_id})\n"
    
    await update.message.reply_text(
        banned_text,
        parse_mode="Markdown"
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ban a user
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to ban users."
        )
        return
    
    # Check if user ID is provided
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Please provide a valid user ID. Usage: /ban <user_id>"
        )
        return
    
    user_id = int(context.args[0])
    
    # Get the user to ban
    ban_user = User.query.get(user_id)
    if not ban_user:
        await update.message.reply_text(
            f"User with ID {user_id} not found."
        )
        return
    
    # Ban the user
    ban_user.is_banned = True
    db.session.commit()
    
    # End all active matches
    active_matches = Match.query.filter(
        (
            (Match.user1_id == ban_user.id) | 
            (Match.user2_id == ban_user.id)
        ),
        Match.is_active == True
    ).all()
    
    for match in active_matches:
        match.is_active = False
        match.ended_at = datetime.utcnow()
        
        # Notify the other user
        other_user_id = match.user2_id if match.user1_id == ban_user.id else match.user1_id
        other_user = User.query.get(other_user_id)
        
        if other_user:
            try:
                await context.bot.send_message(
                    chat_id=other_user.telegram_id,
                    text=f"Your match with {ban_user.full_name} has been ended "
                         f"because they have been banned from the service."
                )
            except Exception as e:
                logger.error(f"Failed to notify user {other_user.id}: {e}")
    
    db.session.commit()
    
    # Notify the banned user
    try:
        await context.bot.send_message(
            chat_id=ban_user.telegram_id,
            text="You have been banned from using this service due to a violation of our terms. "
                 "If you believe this is a mistake, please contact an administrator."
        )
    except Exception as e:
        logger.error(f"Failed to notify banned user {ban_user.id}: {e}")
    
    await update.message.reply_text(
        f"✅ User {ban_user.full_name} (ID: {ban_user.id}) has been banned."
    )

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unban a user
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to unban users."
        )
        return
    
    # Check if user ID is provided
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Please provide a valid user ID. Usage: /unban <user_id>"
        )
        return
    
    user_id = int(context.args[0])
    
    # Get the user to unban
    unban_user = User.query.get(user_id)
    if not unban_user:
        await update.message.reply_text(
            f"User with ID {user_id} not found."
        )
        return
    
    # Unban the user
    unban_user.is_banned = False
    db.session.commit()
    
    # Notify the unbanned user
    try:
        await context.bot.send_message(
            chat_id=unban_user.telegram_id,
            text="Your account has been unbanned. You can now use all features of the service again."
        )
    except Exception as e:
        logger.error(f"Failed to notify unbanned user {unban_user.id}: {e}")
    
    await update.message.reply_text(
        f"✅ User {unban_user.full_name} (ID: {unban_user.id}) has been unbanned."
    )

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle a user report
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data  # report_user_<user_id>
    reported_user_id = int(data.split('_')[-1])
    
    # Get the users
    reporter = User.query.filter_by(telegram_id=user.id).first()
    reported = User.query.get(reported_user_id)
    
    if not reporter or not reported:
        await query.edit_message_text(
            "Error: User not found."
        )
        return ConversationHandler.END
    
    # Store the reported user ID in context
    context.user_data['reported_user_id'] = reported_user_id
    
    # Update user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if user_state:
        user_state.state = STATES["REPORT"]
        user_state.data = {"reported_user_id": reported_user_id}
        db.session.commit()
    else:
        user_state = UserState(
            telegram_id=user.id,
            state=STATES["REPORT"],
            data={"reported_user_id": reported_user_id}
        )
        db.session.add(user_state)
        db.session.commit()
    
    await query.edit_message_text(
        f"You are reporting {reported.full_name}.\n"
        "Please provide a reason for your report.\n\n"
        "Be specific and provide details about what happened."
    )
    
    return STATE_IDS["REPORT_REASON"]

async def process_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the reason for a user report
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        The next state in the conversation
    """
    user = update.effective_user
    reason = update.message.text.strip()
    
    # Check if reason is too short
    if len(reason) < 10:
        await update.message.reply_text(
            "Please provide a more detailed reason for your report."
        )
        return STATE_IDS["REPORT_REASON"]
    
    # Get user state
    user_state = UserState.query.filter_by(telegram_id=user.id).first()
    if not user_state or user_state.state != STATES["REPORT"]:
        await update.message.reply_text(
            "Error: Report session not found. Please try again."
        )
        return ConversationHandler.END
    
    reported_user_id = user_state.data.get("reported_user_id")
    if not reported_user_id:
        await update.message.reply_text(
            "Error: Reported user not found. Please try again."
        )
        return ConversationHandler.END
    
    # Get the users
    reporter = User.query.filter_by(telegram_id=user.id).first()
    reported = User.query.get(reported_user_id)
    
    if not reporter or not reported:
        await update.message.reply_text(
            "Error: User not found."
        )
        return ConversationHandler.END
    
    # Create the report
    report = Report(
        reporter_id=reporter.id,
        reported_user_id=reported.id,
        reason=reason
    )
    db.session.add(report)
    db.session.commit()
    
    # Reset user state
    user_state.state = STATES["IDLE"]
    user_state.data = {}
    db.session.commit()
    
    # Notify the user
    await update.message.reply_text(
        "✅ Your report has been submitted.\n"
        "An administrator will review it as soon as possible.\n"
        "Thank you for helping to keep our community safe."
    )
    
    # Notify admins about the new report
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🚨 *New User Report*\n\n"
                    f"*Reporter:* {reporter.full_name} (ID: {reporter.id})\n"
                    f"*Reported User:* {reported.full_name} (ID: {reported.id})\n"
                    f"*Reason:* {reason}\n"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    return ConversationHandler.END

async def view_pending_confessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show pending confessions for approval
    
    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    
    # Check if user is an admin
    if not await is_admin(user.id):
        await update.message.reply_text(
            "You do not have permission to view pending confessions."
        )
        return
    
    # Get pending confessions
    pending_confessions = Confession.query.filter_by(is_approved=False, is_posted=False).all()
    
    if not pending_confessions:
        await update.message.reply_text(
            "📝 *UniMatchConfessions Moderation*\n\n"
            "There are currently no pending confessions to review.\n\n"
            "_New confessions will appear here when submitted by users._",
            parse_mode="Markdown"
        )
        return
    
    # Display each confession
    for confession in pending_confessions:
        confession_text = (
            f"💌 *Confession #{confession.id}*\n\n"
            f"{confession.content}"
        )
        
        # Create keyboard for admin actions
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_confession_{confession.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_confession_{confession.id}")
            ]
        ])
        
        await context.bot.send_message(
            chat_id=user.id,
            text=confession_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
