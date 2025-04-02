# src/webhook_api.py
from fastapi import FastAPI, Request, HTTPException
import logging
import json
import uvicorn
import os
import traceback
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from src.knowledge_base.retriever import retrieve_answer

# More verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

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

@app.post("/api/shopify-webhook")
async def shopify_webhook(request: Request):
    """Handle incoming webhooks from Shopify"""
    logger.debug("Entering shopify_webhook function")
    
    # Get the webhook payload
    try:
        # Try to get raw body first for logging
        body = await request.body()
        logger.debug(f"Raw webhook payload: {body.decode('utf-8')}")
        
        # Parse JSON
        payload = json.loads(body)
        logger.debug(f"Parsed webhook payload: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError as json_error:
        logger.error(f"JSON Decode Error: {json_error}")
        logger.error(f"Raw payload causing error: {body.decode('utf-8')}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(json_error)}")
    except Exception as e:
        logger.error(f"Unexpected error parsing payload: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
    
    try:
        # Extract the message content with robust parsing
        conversation_id = extract_conversation_id(payload)
        message = extract_message_text(payload)
        sender_id = extract_sender_id(payload)
        
        logger.info(f"Extracted details - Conversation ID: {conversation_id}, Sender ID: {sender_id}")
        
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
        
        # Return the result for testing
        return {
            "status": "success",
            "query": message,
            "response": response,
            "conversation_id": conversation_id,
            "suggested_products": list(session_states[conversation_id].suggested_products)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("webhook_api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))