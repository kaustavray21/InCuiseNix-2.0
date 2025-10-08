import os
import pandas as pd
from django.conf import settings
from langchain_community.document_loaders import DataFrameLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.schema import StrOutputParser

# --- Constants (LLM_MODEL is updated to a valid one) ---
FAISS_INDEX_PATH = os.path.join(settings.BASE_DIR, 'faiss_index')
TRANSCRIPTS_PATH = os.path.join(settings.MEDIA_ROOT, 'transcripts')
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"  # Using a valid, stable model
SIMILARITY_THRESHOLD = 1.5

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

# --- Data Ingestion (No changes needed here, but shown for completeness) ---
def load_all_transcripts():
    """Loads all transcript CSV files into a list of LangChain Documents."""
    all_docs = []
    for course_name in os.listdir(TRANSCRIPTS_PATH):
        course_path = os.path.join(TRANSCRIPTS_PATH, course_name)
        if os.path.isdir(course_path):
            for video_file in os.listdir(course_path):
                if video_file.endswith('.csv'):
                    video_id = video_file.split('.')[0]
                    file_path = os.path.join(course_path, video_file)
                    try:
                        df = pd.read_csv(file_path)
                        df['course_name'] = course_name
                        # Ensure video_id is always a string for consistency
                        df['video_id'] = str(video_id)
                        loader = DataFrameLoader(df, page_content_column='text')
                        docs = loader.load()
                        all_docs.extend(docs)
                    except Exception as e:
                        print(f"Error loading transcript {file_path}: {e}")
    return all_docs

def create_or_update_vector_store():
    """Loads transcripts, creates a FAISS index from them, and saves it to disk."""
    print("Loading transcripts...")
    documents = load_all_transcripts()
    if not documents:
        print("No documents found to process.")
        return
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_documents = text_splitter.split_documents(documents)
    print(f"Splitting documents into {len(split_documents)} chunks.")
    print("Creating new FAISS index... This may take a while.")
    embedding_function = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY
    )
    db = FAISS.from_documents(split_documents, embedding_function)
    db.save_local(FAISS_INDEX_PATH)
    print(f"FAISS index created and saved to '{FAISS_INDEX_PATH}'")


# --- NEW, SMARTER RAG AND ROUTING LOGIC ---

def get_rag_chain(retriever):
    """Creates a RAG chain with a specific retriever."""
    prompt_template = """
    You are an expert AI assistant for the InCuiseNix e-learning platform.
    Your goal is to provide accurate and helpful answers.

    Answer the QUESTION based on the CONTEXT provided below.
    If the context is empty or does not contain the answer, state that you cannot answer based on the video content.

    CONTEXT:
    {context}

    QUESTION:
    {question}
    """
    prompt = PromptTemplate.from_template(prompt_template)
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)

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
    
    # We only need to pass the question to this chain
    return (
        RunnablePassthrough()
        | prompt
        | llm
        | StrOutputParser()
    )

def query_router(query, video_id=None):
    """
    Routes the query to the appropriate chain (RAG or General) based on context availability.
    This is the new hybrid logic.
    """
    store = get_vector_store()
    if not store:
        print("FAISS index not found. Routing to general chain as a fallback.")
        return get_general_chain().invoke(query)

    # 1. Always try to use the video-specific retriever first if a video_id is given.
    if video_id:
        print(f"Attempting RAG search for video_id: {video_id}...")
        # FIX: Ensure video_id is a string for consistent filtering
        retriever = store.as_retriever(
            search_kwargs={'k': 5, 'filter': {'video_id': str(video_id)}}
        )
        
        # 2. Check if the retriever finds any relevant documents for the query.
        relevant_docs = retriever.get_relevant_documents(query)
        
        if relevant_docs:
            print(f"Found {len(relevant_docs)} relevant documents. Using RAG chain.")
            # Format documents into a string context
            context_str = "\n\n".join([doc.page_content for doc in relevant_docs])
            return get_rag_chain(retriever).invoke(query)
        else:
            print("No relevant documents found in the video. Routing to general knowledge chain.")
            return get_general_chain().invoke(query)

    # 3. If no video_id was ever provided, use the general chain.
    else:
        print("No video_id provided. Routing to general knowledge chain.")
        return get_general_chain().invoke(query)