import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
import json

# Import bot initialization function
from bot import initialize_bot

# Initialize logger
logger = logging.getLogger(__name__)

def setup_webhook(app: Flask, bot: Application, token: str):
    """
    Set up the webhook endpoint for the Telegram bot
    
    Args:
        app: The Flask app
        bot: The bot application
        token: The bot token for route security
    """
    webhook_url_path = f"/webhook/{token}"
    
    @app.route(webhook_url_path, methods=["POST"])
    async def webhook():
        """Process incoming webhook updates from Telegram"""
        if request.method == "POST":
            try:
                # Get the update data
                update_data = request.get_json(force=True)
                logger.debug(f"Received update: {json.dumps(update_data, indent=2)}")
                
                # Initialize the bot if needed
                try:
                    await initialize_bot(bot)
                except Exception as e:
                    logger.warning(f"Bot initialization warning: {e}")
                
                # Convert to a Telegram Update object
                update = Update.de_json(update_data, bot.bot)
                
                # Process the update in a background task to avoid blocking
                asyncio.create_task(bot.process_update(update))
                
                # Return success immediately
                return jsonify({"status": "success"})
            except Exception as e:
                logger.error(f"Error processing update: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            return jsonify({"status": "error", "message": "Method not allowed"}), 405
    
    # Webhook ping endpoint removed - using the one in main.py instead
    
    @app.route("/set_webhook", methods=["GET"])
    async def set_webhook():
        """Set the webhook URL for the bot"""
        # Get the webhook URL from the request
        webhook_url = request.args.get("url")
        if not webhook_url:
            return jsonify({"status": "error", "message": "No webhook URL provided"}), 400
        
        # Append the token path
        webhook_url = f"{webhook_url.rstrip('/')}{webhook_url_path}"
        
        try:
            # Initialize the bot
            try:
                await initialize_bot(bot)
            except Exception as e:
                logger.warning(f"Bot initialization warning: {e}")
                
            # Set the webhook
            await bot.bot.set_webhook(url=webhook_url)
            return jsonify({
                "status": "success",
                "message": f"Webhook set to {webhook_url}"
            })
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    @app.route("/remove_webhook", methods=["GET"])
    async def remove_webhook():
        """Remove the webhook"""
        try:
            # Initialize the bot
            try:
                await initialize_bot(bot)
            except Exception as e:
                logger.warning(f"Bot initialization warning: {e}")
            
            # Remove the webhook
            await bot.bot.delete_webhook()
            return jsonify({
                "status": "success",
                "message": "Webhook removed"
            })
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    logger.info(f"Webhook endpoint set up at {webhook_url_path}")
