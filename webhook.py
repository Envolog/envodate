import logging
import asyncio
import traceback
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
    
    @app.route(webhook_url_path, methods=["POST", "GET"])
    def webhook():
        """Process incoming webhook updates from Telegram"""
        # Handle GET requests (for testing)
        if request.method == "GET":
            return jsonify({"status": "success", "message": "Webhook endpoint is active"}), 200
            
        # Handle POST requests (actual updates)
        if request.method == "POST":
            try:
                # Get the update data
                try:
                    update_data = request.get_json(force=True)
                    logger.info(f"Received update from Telegram")
                    logger.debug(f"Update data: {json.dumps(update_data, indent=2)}")
                except Exception as e:
                    logger.error(f"Failed to parse update JSON: {e}")
                    return jsonify({"status": "success", "message": "Could not parse update data"}), 200
                
                # Convert to a Telegram Update object
                try:
                    update = Update.de_json(update_data, bot.bot)
                except Exception as e:
                    logger.error(f"Failed to convert update: {e}")
                    return jsonify({"status": "success", "message": "Invalid update format"}), 200
                
                # Initialize the bot if needed
                try:
                    # Use synchronous application method for webhook context
                    bot.create_task(initialize_bot(bot))
                    logger.info("Bot initialization task created")
                except Exception as e:
                    logger.error(f"Bot initialization error: {e}")
                    # Continue processing even if initialization has issues
                
                # Process the update
                try:
                    # Use the application's own processing logic
                    # This avoids the need for manual event loop management
                    bot.create_task(bot.process_update(update))
                    logger.info("Update processing task created")
                except Exception as e:
                    logger.error(f"Failed to process update: {e}")
                    # Continue and return success anyway
                
                # Always return success to Telegram
                return jsonify({"status": "success"})
            except Exception as e:
                # Get detailed traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Webhook error: {str(e)}")
                logger.error(f"Traceback: {error_traceback}")
                # Always return 200 OK to Telegram to prevent retries
                return jsonify({"status": "success", "message": "Error handled"}), 200
        else:
            return jsonify({"status": "success", "message": "Method not allowed"}), 200
    
    # Webhook ping endpoint removed - using the one in main.py instead
    
    @app.route("/set_webhook", methods=["GET"])
    def set_webhook():
        """Set the webhook URL for the bot"""
        # Get the webhook URL from the request
        webhook_url = request.args.get("url")
        if not webhook_url:
            return jsonify({"status": "error", "message": "No webhook URL provided"}), 400
        
        # Append the token path
        webhook_url = f"{webhook_url.rstrip('/')}{webhook_url_path}"
        
        try:
            # Use the bot's create_task method to handle async operations
            # This is more reliable than manually creating event loops
            future = bot.create_task(bot.bot.set_webhook(url=webhook_url))
            
            # Return success immediately rather than waiting for completion
            logger.info(f"Webhook setting task created for URL: {webhook_url}")
            return jsonify({
                "status": "success", 
                "message": f"Setting webhook to {webhook_url}"
            })
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    @app.route("/remove_webhook", methods=["GET"])
    def remove_webhook():
        """Remove the webhook"""
        try:
            # Use the bot's create_task method to handle async operations
            # This is more reliable than manually creating event loops
            future = bot.create_task(bot.bot.delete_webhook())
            
            # Return success immediately rather than waiting for completion
            logger.info("Webhook removal task created")
            return jsonify({
                "status": "success",
                "message": "Removing webhook"
            })
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    logger.info(f"Webhook endpoint set up at {webhook_url_path}")
