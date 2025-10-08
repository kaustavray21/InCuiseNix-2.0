import os
import re # Import the regular expression module
import pandas as pd
from django.conf import settings
from langchain_community.document_loaders import DataFrameLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import StrOutputParser

# --- Constants ---
FAISS_INDEX_PATH = os.path.join(settings.BASE_DIR, 'faiss_index')
TRANSCRIPTS_PATH = os.path.join(settings.MEDIA_ROOT, 'transcripts')
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"

# --- Global variable ---
vector_store = None

def get_vector_store():
    """Loads the FAISS index from disk if it exists, otherwise returns None."""
    global vector_store
    if vector_store is None:
        embedding_function = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=settings.GEMINI_API_KEY
        )
        if os.path.exists(FAISS_INDEX_PATH):
            print("Loading existing FAISS index from disk...")
            vector_store = FAISS.load_local(
                FAISS_INDEX_PATH,
                embedding_function,
                allow_dangerous_deserialization=True
            )
            print("FAISS index loaded.")
        else:
            print("No FAISS index found. It will be created during the ingestion process.")
    return vector_store

# ... (Data Ingestion functions remain the same) ...

# --- NEW: Helper function to parse timestamps from a query ---
def parse_timestamp_from_query(query):
    """
    Finds a timestamp in formats like HH:MM:SS, MM:SS, or SS in a query
    and converts it to total seconds.
    """
    # Regex to find timestamps like 01:23:45, 23:45, or :45
    match = re.search(r'(\d{1,2}):(\d{1,2}):(\d{1,2})|(\d{1,2}):(\d{1,2})', query)
    if not match:
        return None
    
    # Extract matched groups, filtering out None values
    time_parts_str = [p for p in match.groups() if p is not None]
    time_parts = [int(p) for p in time_parts_str]

    seconds = 0
    if len(time_parts) == 3: # HH:MM:SS
        seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
    elif len(time_parts) == 2: # MM:SS
        seconds = time_parts[0] * 60 + time_parts[1]
    
    return seconds if seconds > 0 else None


# --- RAG and General Chains (remain the same) ---
def get_rag_chain(retriever):
    """Creates a RAG chain with a specific retriever."""
    prompt_template = """
    You are an expert AI assistant for the InCuiseNix e-learning platform.
    Your goal is to provide accurate and helpful answers.
    Answer the QUESTION based on the CONTEXT provided below from the video transcript.
    If the context is empty or does not contain the answer, state that you cannot answer based on the video content.
    CONTEXT:
    {context}
    QUESTION:
    {question}
    """
    prompt = PromptTemplate.from_template(prompt_template)
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)

    # The chain now formats the retrieved documents into the context
    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

def get_general_chain():
    """Creates a chain for general knowledge questions."""
    general_prompt_template = "You are a helpful AI assistant. Answer the following question to the best of your ability.\nQuestion: {question}"
    prompt = PromptTemplate.from_template(general_prompt_template)
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)
    
    return (
        RunnablePassthrough()
        | prompt
        | llm
        | StrOutputParser()
    )


# --- UPDATED: The Query Router is now much smarter ---
def query_router(query, video_id=None, video_title=None, timestamp=0):
    """
    Routes the query to the correct chain: Timestamp-based, RAG, or General.
    """
    store = get_vector_store()
    if not store:
        print("FAISS index not found. Routing to general chain.")
        return get_general_chain().invoke({"question": query})

    # --- NEW: Time-sensitive routing logic ---
    query_timestamp = parse_timestamp_from_query(query)
    effective_timestamp = query_timestamp if query_timestamp is not None else timestamp
    
    time_keywords = ['at this moment', 'right now', 'at this time', 'what is he saying', 'what does this mean']
    is_time_sensitive = query_timestamp is not None or any(keyword in query.lower() for keyword in time_keywords)

    if video_id and is_time_sensitive:
        print(f"Time-sensitive query detected for timestamp: {effective_timestamp}s")
        # For timestamp queries, we retrieve all docs for the video and filter in Python.
        # This is more precise than a vector search for finding a specific time.
        retriever = store.as_retriever(search_kwargs={'k': 300, 'filter': {'video_id': str(video_id)}})
        all_video_docs = retriever.get_relevant_documents("") # Empty query gets all filtered docs
        
        target_doc = None
        for doc in all_video_docs:
            start_time = doc.metadata.get('start', 0)
            end_time = doc.metadata.get('end', 0)
            if start_time <= effective_timestamp < end_time:
                target_doc = doc
                break
        
        if target_doc:
            context = target_doc.page_content
            print(f"Found transcript chunk for the timestamp: '{context}'")
            # Create a very specific prompt for the LLM
            question_with_context = (
                f"The user is watching a video titled '{video_title}'. "
                f"At the moment {int(effective_timestamp // 60)} minutes and {int(effective_timestamp % 60)} seconds, "
                f"the transcript says: '{context}'. "
                f"Based *only* on this transcript snippet, answer the user's question: '{query}'"
            )
            # Use the general chain as it's good at direct instruction following
            return get_general_chain().invoke({"question": question_with_context})
        else:
            print("Could not find a transcript chunk for the specified timestamp.")
            return "I couldn't find the specific part of the transcript for that time. Please try a different timestamp."

    # --- Fallback to standard RAG and General logic ---
    print("Standard query detected. Using semantic search.")
    if video_id:
        retriever = store.as_retriever(
            search_kwargs={'k': 5, 'filter': {'video_id': str(video_id)}}
        )
        relevant_docs = retriever.get_relevant_documents(query)
        
        if relevant_docs:
            contextual_query = f"Regarding the video '{video_title}', {query}"
            return get_rag_chain(retriever).invoke(contextual_query)
        else:
            print("No relevant documents found for the query. Using general knowledge.")
            return get_general_chain().invoke({"question": query})

    print("No video_id provided. Routing to general knowledge chain.")
    return get_general_chain().invoke({"question": query})