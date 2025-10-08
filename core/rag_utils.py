import os
import pandas as pd
from django.conf import settings

# --- FAISS and LangChain Imports ---
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
LLM_MODEL = "gemini-2.5-pro" # As per your provided code
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
            vector_store = FAISS.load_local(FAISS_INDEX_PATH, embedding_function, allow_dangerous_deserialization=True)
            print("FAISS index loaded.")
        else:
            print("No FAISS index found. It will be created during the ingestion process.")
    return vector_store

# --- Core RAG Functions ---

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
                        df['video_id'] = video_id
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


# --- UPDATED RAG CHAIN FUNCTION ---
def get_rag_chain(video_id):
    """
    Creates and returns a RAG chain that is FILTERED to a specific video_id.
    """
    store = get_vector_store()
    if not store:
        raise Exception("FAISS index not found or loaded.")

    # --- THE CRITICAL CHANGE ---
    # Create a retriever that filters the search by the video_id metadata field
    retriever = store.as_retriever(
        search_kwargs={
            'k': 5, # Retrieve the top 5 most relevant chunks
            'filter': {'video_id': video_id}
        }
    )
    
    prompt_template = """
    You are an expert AI assistant for the InCuiseNix e-learning platform.
    Your goal is to provide accurate and helpful answers based on the transcript of the current video.
    CONTEXT: {context}
    QUESTION: {question}
    Answer the question based ONLY on the context provided. If the context does not contain the answer,
    state that you cannot answer the question based on the available video content.
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
    """Creates and returns a simple LangChain runnable for general questions."""
    general_prompt_template = "You are a helpful AI assistant. Answer the following question.\nQuestion: {question}"
    prompt = PromptTemplate.from_template(general_prompt_template)
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)
    return prompt | llm | StrOutputParser()

# --- UPDATED QUERY ROUTER FUNCTION ---
def query_router(query, video_id=None):
    """
    If a video_id is provided, routes to a filtered RAG chain for that video.
    Otherwise, it performs a general search across all videos.
    """
    store = get_vector_store()
    if not store:
        # If the index doesn't exist, we can only answer general questions.
        print("FAISS index not found. Routing to general chain as a fallback.")
        return get_general_chain()

    # If a video_id is passed from the frontend, ALWAYS use the filtered RAG chain.
    if video_id:
        print(f"Query routed to: RAG Chain (Filtered for video_id: {video_id})")
        return get_rag_chain(video_id)

    # --- Fallback Logic (if for some reason no video_id is sent) ---
    print("No video_id provided. Performing a general search across all videos.")
    results_with_scores = store.similarity_search_with_relevance_scores(query, k=1)
    
    if results_with_scores:
        top_result_score = results_with_scores[0][1]
        print(f"Top result similarity score: {top_result_score}")
        if top_result_score < SIMILARITY_THRESHOLD:
            # Get the video_id from the metadata of the best matching document
            matched_video_id = results_with_scores[0][0].metadata.get('video_id')
            if matched_video_id:
                print(f"Query routed to: RAG Chain (Fallback to best match from video_id: {matched_video_id})")
                return get_rag_chain(matched_video_id)
    
    print("Query routed to: General Chain")
    return get_general_chain()