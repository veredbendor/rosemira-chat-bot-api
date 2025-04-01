# src/webhook_api.py
from fastapi import FastAPI, Request, HTTPException
import logging
import json
import uvicorn
import os
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from src.knowledge_base.retriever import retrieve_answer
from src.services.shopify_chat_service import ShopifyChatService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize the shopify chat service
shopify_chat_service = ShopifyChatService()

# Store conversation memories by conversation ID
conversation_memories = {}

# Store session states by conversation ID
session_states = {}

class WebhookSessionState:
    """Simple class to mimic Streamlit's session state for the webhook API"""
    def __init__(self):
        self.suggested_products = set()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "service": "Rosemira Chat Bot API"}

@app.post("/api/shopify-webhook")
async def shopify_webhook(request: Request):
    """Handle incoming webhooks from Shopify"""
    logger.info("Received webhook from Shopify")
    
    # Get the webhook payload
    try:
        payload = await request.json()
        logger.info(f"Webhook payload: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    try:
        # Extract the message content with robust parsing for different formats
        conversation_id = extract_conversation_id(payload)
        message = extract_message_text(payload)
        sender_id = extract_sender_id(payload)
        
        if not message:
            logger.warning("No message text found in payload")
            return {"status": "error", "detail": "No message text found in payload"}
        
        logger.info(f"Processing message: '{message}' from conversation {conversation_id}")
        
        # Get or create memory for this conversation
        if conversation_id not in conversation_memories:
            logger.info(f"Creating new conversation memory for {conversation_id}")
            conversation_memories[conversation_id] = ConversationBufferMemory(memory_key="history", return_messages=True)
        
        # Get or create session state for this conversation
        if conversation_id not in session_states:
            logger.info(f"Creating new session state for {conversation_id}")
            session_states[conversation_id] = WebhookSessionState()
        
        # Generate response using your existing RAG pipeline
        response = get_answer(
            message, 
            conversation_memories[conversation_id], 
            session_states[conversation_id]
        )
        
        # Log the response
        logger.info(f"Generated response: {response}")
        
        # For development, don't actually call the Shopify API
        # Uncomment this in production
        # response_result = shopify_chat_service.send_chat_response(conversation_id, response)
        
        # Return the result for testing
        return {
            "status": "success",
            "query": message,
            "response": response,
            "conversation_id": conversation_id,
            "suggested_products": list(session_states[conversation_id].suggested_products)
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def extract_conversation_id(payload):
    """Extract conversation ID with fallbacks for different payload formats"""
    # Try different possible locations for the conversation ID
    conversation_id = payload.get('conversation_id')
    
    if not conversation_id:
        conversation_id = payload.get('conversation', {}).get('id')
    
    if not conversation_id:
        conversation_id = payload.get('data', {}).get('conversation_id')
    
    if not conversation_id:
        conversation_id = payload.get('data', {}).get('conversation', {}).get('id')
    
    # If still not found, use a default for testing
    if not conversation_id:
        conversation_id = "unknown_conversation"
        
    return conversation_id

def extract_message_text(payload):
    """Extract message text with fallbacks for different payload formats"""
    # Try different possible message formats
    message = payload.get('message', {}).get('text', '')
    
    if not message:
        message = payload.get('data', {}).get('message', {}).get('text', '')
    
    if not message:
        message = payload.get('content', '')
    
    if not message:
        message = payload.get('data', {}).get('content', '')
    
    return message

def extract_sender_id(payload):
    """Extract sender ID with fallbacks"""
    sender_id = payload.get('sender', {}).get('id')
    
    if not sender_id:
        sender_id = payload.get('data', {}).get('sender', {}).get('id')
    
    if not sender_id:
        sender_id = payload.get('author_id')
    
    if not sender_id:
        sender_id = "unknown_sender"
        
    return sender_id

def get_answer(query: str, memory, session_state) -> str:
    """
    Generate an answer to the user's query using session-specific conversation memory.
    This mirrors the function in faq_service.py
    """
    # Retrieve the contextually constructed prompt
    prompt = retrieve_answer(query, memory, session_state)

    # Create the conversation chain with memory
    conversation_chain = ConversationChain(
        llm=ChatOpenAI(),
        memory=memory
    )

    # Generate a response using the conversation chain
    response = conversation_chain.run(input=prompt)
    return response.strip()

if __name__ == "__main__":
    uvicorn.run("webhook_api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))