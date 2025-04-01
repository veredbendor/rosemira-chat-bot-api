# src/services/shopify_chat_service.py
import requests
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ShopifyChatService:
    def __init__(self):
        """Initialize Shopify Chat API client with credentials from environment variables"""
        self.api_key = os.getenv("SHOPIFY_API_KEY")
        self.api_secret = os.getenv("SHOPIFY_API_SECRET")
        self.shop_url = os.getenv("SHOPIFY_SHOP_URL")
        self.api_version = os.getenv("SHOPIFY_API_VERSION", "2023-07")
        
    def send_chat_response(self, conversation_id, message):
        """
        Send a response to a Shopify chat conversation
        
        Args:
            conversation_id (str): The Shopify conversation ID
            message (str): The message to send
            
        Returns:
            dict: The response from Shopify
        """
        logger.info(f"Sending response to Shopify conversation {conversation_id}")
        
        # This endpoint needs to be updated based on Shopify's actual Chat API
        url = f"{self.shop_url}/api/chat/conversations/{conversation_id}/messages"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.api_key
        }
        
        payload = {
            "message": message,
            "author": "bot"  # Adjust based on Shopify's API requirements
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Successfully sent message to Shopify")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to Shopify: {str(e)}")
            raise