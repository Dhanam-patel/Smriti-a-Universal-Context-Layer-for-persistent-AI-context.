def read_context(chat: str, query: str, user_info: dict):
    """
    Retrieves semantically relevant context from a selected UCL chat namespace.
    """
    # 1. Generate embedding for query using OpenAI
    # 2. Query Pinecone namespace specific to `chat`
    # 3. Return stringified context
    
    return f"Placeholder context for {chat} about {query}"
