from telegram.ext import ApplicationBuilder, Application
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Bot instance
bot_app = None

async def initialize_bot(bot_app: Application) -> None:
    """
    Initialize the bot application if not already initialized
    
    Args:
        bot_app: The bot application to initialize
    """
    try:
        # We'll use our own tracking for these states
        initialized = getattr(bot_app, "_custom_initialized", False)
        running = getattr(bot_app, "_custom_running", False)
        
        if not initialized:
            logger.info("Initializing bot application...")
            await bot_app.initialize()
            # Store our own tracking flag
            setattr(bot_app, "_custom_initialized", True)
            logger.info("Bot application initialized successfully")
        
        if not running:
            logger.info("Starting bot application...")
            await bot_app.start()
            # Store our own tracking flag
            setattr(bot_app, "_custom_running", True)
            logger.info("Bot application started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize or start bot: {str(e)}")
        # Continue execution rather than raising
        # This allows the webhook to still function even if bot init fails
        logger.warning("Continuing execution despite initialization error")
    
import asyncio
import threading

def setup_bot(token: str) -> Application:
    """
    Set up the Telegram bot application
    
    Args:
        token: The Telegram bot token
        
    Returns:
        The configured Application instance
    """
    global bot_app
    
    logger.info("Setting up the bot application...")
    
    # Build the application with token
    bot_app = ApplicationBuilder().token(token).build()
    
    # Import handlers here to avoid circular imports
    from bot.handlers import register_handlers
    register_handlers(bot_app)
    
    # Start initialization in a background thread to avoid blocking
    def init_bot_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(initialize_bot(bot_app))
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
    
    threading.Thread(target=init_bot_async, daemon=True).start()
    
    logger.info("Bot setup complete")
    return bot_app

def get_bot() -> Application:
    """
    Get the bot application instance
    
    Returns:
        The Application instance
    """
    if bot_app is None:
        raise ValueError("Bot application not initialized. Call setup_bot first.")
    return bot_app
