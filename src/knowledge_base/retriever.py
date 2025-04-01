import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

# FAISS storage path
FAISS_INDEX_PATH = "faiss_index"
FAISS_INDEX_FILE = os.path.join(FAISS_INDEX_PATH, "index.faiss")

def ensure_faiss_index_exists():
    """
    Ensure the FAISS index exists. If missing, create a simple placeholder.
    """
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

    if not os.path.exists(FAISS_INDEX_FILE):
        print("⚠️ FAISS index not found. Creating a simple placeholder index.")
        # Create some simple documents
        documents = [
            Document(
                page_content="Rosemira offers organic skincare products for sensitive skin.",
                metadata={"product": True, "title": "Gentle Cleanser", "product_type": "Cleanser"}
            ),
            Document(
                page_content="Our moisturizers are fragrance-free and suitable for all skin types.",
                metadata={"product": True, "title": "Hydrating Moisturizer", "product_type": "Moisturizer"}
            ),
            Document(
                page_content="We offer free shipping on orders over $50.",
                metadata={"conversation": True, "topic": "shipping"}
            )
        ]
        
        # Create and save a simple index
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.from_documents(documents, embeddings)
        vector_store.save_local(FAISS_INDEX_PATH)

def construct_prompt(query: str, conversations, products=None, session_state=None) -> str:
    """
    Construct a response prompt with optional product recommendations.
    """
    prompt = (
        "You are a knowledgeable representative of Rosemira, a trusted provider of skincare solutions.\n\n"
        f"User Query: \"{query}\"\n\n"
    )

    # Include relevant past conversations if available
    if conversations:
        prompt += "Relevant Past Conversations:\n"
        for i, conv in enumerate(conversations, 1):
            prompt += f"{i}. {conv.page_content.strip()}\n"

    # Include product recommendations if applicable
    if products and session_state:
        suggested_products = session_state.suggested_products
        new_products = []

        for product in products:
            product_title = product.metadata.get('title', 'Product Name Unknown')
            product_type = product.metadata.get('product_type', 'Uncategorized')

            # Only suggest new products that haven't been recommended yet
            if product_title not in suggested_products:
                new_products.append((product_type, product_title))
                suggested_products.add(product_title)  # Track suggested products

        # Group new products by category
        if new_products:
            prompt += "\nRecommended Products by Category:\n"
            category_dict = {}
            for product_type, product_title in new_products:
                category_dict.setdefault(product_type, []).append(product_title)

            for category, product_list in category_dict.items():
                prompt += f"\n{category}:\n"
                for product in product_list:
                    prompt += f"- {product}\n"

    prompt += (
        "\nBased on the user's query and any past interactions, provide a clear, concise, and informative response. "
        "Avoid suggesting products already mentioned in the conversation."
    )

    return prompt

def retrieve_answer(query: str, memory, session_state) -> str:
    """
    Retrieves an answer to a query using FAISS.
    """
    # Ensure FAISS index is available before proceeding
    ensure_faiss_index_exists()

    # Load FAISS index safely
    try:
        vector_store = FAISS.load_local(FAISS_INDEX_PATH, OpenAIEmbeddings(), allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        return construct_prompt(query, [])  # Fallback to a simple prompt

    # Perform similarity search
    docs = vector_store.similarity_search(query, k=3)

    # Separate conversations and products
    conversations = [doc for doc in docs if "conversation" in doc.metadata]
    products = [doc for doc in docs if "product" in doc.metadata]

    # Detect if the user is requesting recommendations
    recommendation_keywords = ["recommend", "suggest", "product", "what should I use"]
    is_recommendation_query = any(keyword in query.lower() for keyword in recommendation_keywords)

    # Construct the appropriate prompt based on query intent
    if is_recommendation_query:
        return construct_prompt(query, conversations, products, session_state)
    else:
        return construct_prompt(query, conversations)

# Ensure FAISS Index Exists at Startup
ensure_faiss_index_exists()