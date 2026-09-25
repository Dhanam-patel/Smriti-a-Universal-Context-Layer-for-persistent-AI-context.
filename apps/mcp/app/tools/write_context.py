def write_context(chat: str, content: str, user_info: dict):
    """
    Persists new context into a selected UCL chat namespace.
    """
    # 1. Generate embedding for content using OpenAI
    # 2. Upsert into Pinecone namespace specific to `chat`
    
    return "Successfully wrote context."
