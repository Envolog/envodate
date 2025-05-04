import os
import logging
from flask import jsonify
from app import app
from webhook import setup_webhook
from bot import setup_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
