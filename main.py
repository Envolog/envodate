import os
import logging
from flask import jsonify, request
from app import app
from webhook import setup_webhook
from bot import setup_bot

# Configure detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set to DEBUG to get more detailed logs
)
logger = logging.getLogger(__name__)

# Add a specific logger for werkzeug (Flask)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# Add a specific logger for telegram
telegram_logger = logging.getLogger('telegram')
telegram_logger.setLevel(logging.DEBUG)

# Log startup information
logger.info("Starting UniMatch Ethiopia Telegram Bot application")

# Initialize database and models
import models  # This is needed to ensure models are loaded

# Default routes for health checks
@app.route('/')
def index():
    return jsonify({
        'status': 'success',
        'message': 'Telegram Dating Bot API is running',
        'service': 'Ethiopian University Dating Bot'
    })

@app.route('/ping')
def ping():
    return jsonify({
        'status': 'success',
        'message': 'Bot is running'
    })

@app.route('/api/docs')
def api_docs():
    return jsonify({
        'status': 'success',
        'api_version': '1.0',
        'service': 'Ethiopian University Dating Bot API',
        'endpoints': [
            {
                'path': '/',
                'method': 'GET',
                'description': 'API health check and service information'
            },
            {
                'path': '/ping',
                'method': 'GET',
                'description': 'Simple health check endpoint'
            },
            {
                'path': '/about',
                'method': 'GET',
                'description': 'Information about the bot and its developer'
            },
            {
                'path': '/api/docs',
                'method': 'GET',
                'description': 'API documentation and available endpoints'
            },
            {
                'path': '/webhook/{token}',
                'method': 'POST',
                'description': 'Telegram webhook endpoint (requires valid token)'
            },
            {
                'path': '/set_webhook',
                'method': 'GET',
                'description': 'Configure the webhook URL for the Telegram bot (requires token)'
            },
            {
                'path': '/remove_webhook',
                'method': 'GET',
                'description': 'Remove the webhook from the Telegram bot (requires token)'
            },
            {
                'path': '/setup_webhook_direct',
                'method': 'GET',
                'description': 'Direct webhook setup without external URL requirements'
            },
            {
                'path': '/delete_webhook_direct',
                'method': 'GET',
                'description': 'Direct webhook deletion'
            }
        ]
    })

@app.route('/about')
def about():
    return jsonify({
        'status': 'success',
        'bot_name': 'Ethiopian University Dating Bot',
        'version': '1.0',
        'description': 'A Telegram bot dating service for Ethiopian university students with user matching, in-bot messaging, and anonymous confessions.',
        'features': [
            'User Registration and Profile Creation',
            'Smart Matching Algorithm',
            'Private In-Bot Messaging',
            'Anonymous Confessions Channel',
            'Report and Moderation System',
            'University-Specific Matching'
        ],
        'developer': '@envologia',
        'project_date': 'May 2025',
        'contact': 'For support or feature requests, please contact @envologia on Telegram',
        'supported_universities': [
            'Addis Ababa University',
            'Bahir Dar University',
            'Hawassa University',
            'Jimma University',
            'Mekelle University',
            'Gondar University',
            'Adama Science and Technology University',
            'Haramaya University',
            'Arba Minch University',
            'Dire Dawa University'
        ]
    })

# Setup webhook if running as main
if __name__ == "__main__":
    # Setup bot and webhook
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        exit(1)
    
    bot = setup_bot(token)
    setup_webhook(app, bot, token)
    
    # Run the Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Direct webhook management routes
@app.route('/setup_webhook_direct')
def setup_webhook_direct():
    """Set up webhook directly from the current host"""
    import asyncio
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return jsonify({"status": "error", "message": "No bot token available"}), 400
    
    try:
        # Get the request host
        host = request.host_url.rstrip('/')
        webhook_path = f"/webhook/{token}"
        webhook_url = f"{host}{webhook_path}"
        
        # Get the bot instance
        from bot import get_bot
        bot_instance = get_bot()
        
        # Create a new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Delete any existing webhook
        try:
            loop.run_until_complete(bot_instance.bot.delete_webhook())
            logger.info("Existing webhook deleted")
        except Exception as e:
            logger.warning(f"Error deleting existing webhook: {e}")
        
        # Set the new webhook
        loop.run_until_complete(bot_instance.bot.set_webhook(url=webhook_url))
        
        return jsonify({
            "status": "success", 
            "message": f"Webhook set to {webhook_url}"
        })
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_webhook_direct')
def delete_webhook_direct():
    """Delete the current webhook"""
    import asyncio
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return jsonify({"status": "error", "message": "No bot token available"}), 400
    
    try:
        # Get the bot instance
        from bot import get_bot
        bot_instance = get_bot()
        
        # Create a new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Delete the webhook
        loop.run_until_complete(bot_instance.bot.delete_webhook())
        
        return jsonify({
            "status": "success", 
            "message": "Webhook deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Manual URL webhook setup route
@app.route('/set_webhook_url')
def set_webhook_url():
    """Set webhook to a specific URL"""
    import asyncio
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return jsonify({"status": "error", "message": "No bot token available"}), 400
    
    # Get URL from query parameter
    url = request.args.get('url')
    
    # If URL is not provided, show a simple form
    if not url:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Set Webhook URL</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                form { max-width: 500px; margin: 0 auto; }
                input[type=text] { width: 100%; padding: 8px; margin: 10px 0; }
                button { background: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
                h1 { color: #333; }
                .note { color: #666; font-size: 14px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <h1>Set Telegram Webhook URL</h1>
            <form method="GET" action="/set_webhook_url">
                <p>Enter the base URL of your application (e.g., https://your-app.onrender.com):</p>
                <input type="text" name="url" placeholder="https://your-app.onrender.com" required>
                <button type="submit">Set Webhook</button>
            </form>
            <div class="note">
                <p>Note: This will automatically append /webhook/TOKEN to your URL.</p>
                <p>Current environment: """ + request.host_url + """</p>
            </div>
        </body>
        </html>
        """
    
    try:
        # Format the webhook URL
        webhook_path = f"/webhook/{token}"
        if not url.endswith('/'):
            url += '/'
        webhook_url = f"{url.rstrip('/')}{webhook_path}"
        
        # Get the bot instance
        from bot import get_bot
        bot_instance = get_bot()
        
        # Create a new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Delete any existing webhook
        try:
            loop.run_until_complete(bot_instance.bot.delete_webhook())
            logger.info("Existing webhook deleted")
        except Exception as e:
            logger.warning(f"Error deleting existing webhook: {e}")
        
        # Set the new webhook
        loop.run_until_complete(bot_instance.bot.set_webhook(url=webhook_url))
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Webhook Set Successfully</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .success {{ color: green; background: #e8f5e9; padding: 15px; border-radius: 4px; }}
                h1 {{ color: #333; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow: auto; }}
            </style>
        </head>
        <body>
            <h1>Webhook Set Successfully</h1>
            <div class="success">
                <p>Your webhook has been successfully set to:</p>
                <pre>{webhook_url}</pre>
                <p>You can now interact with your bot on Telegram.</p>
            </div>
            <p><a href="/">Return to main page</a></p>
        </body>
        </html>
        """
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error setting webhook: {error_message}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Webhook Setup Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .error {{ color: red; background: #ffebee; padding: 15px; border-radius: 4px; }}
                h1 {{ color: #333; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow: auto; }}
            </style>
        </head>
        <body>
            <h1>Webhook Setup Error</h1>
            <div class="error">
                <p>There was an error setting your webhook:</p>
                <pre>{error_message}</pre>
            </div>
            <p><a href="/set_webhook_url">Try again</a> | <a href="/">Return to main page</a></p>
        </body>
        </html>
        """

# For gunicorn
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if token:
    try:
        bot = setup_bot(token)
        setup_webhook(app, bot, token)
        logger.info("Bot and webhook set up successfully")
    except Exception as e:
        logger.error(f"Error setting up bot and webhook: {e}")
        # Continue without bot if token is missing - will show basic Flask app only
else:
    logger.warning("TELEGRAM_BOT_TOKEN not set, running in API-only mode")
