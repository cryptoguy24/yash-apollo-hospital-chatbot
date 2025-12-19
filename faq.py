# Standard library imports - for file paths, unique IDs, and environment variables
import os
import uuid
from pathlib import Path

# Data handling - for reading and processing CSV files
import pandas as pd

# Configuration management - for loading API keys and settings from .env file
from dotenv import load_dotenv

# Vector database operations - for storing and searching FAQs using embeddings
import chromadb
from chromadb.utils import embedding_functions

# AI/LLM operations - for generating intelligent responses using language models
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

# Load environment variables (like API keys) from the .env file
load_dotenv()

# Set up the path to the FAQ CSV file (it's in the 'data' folder)
faqs_path = Path(__file__).parent / 'data/faq.csv'

# Connect to ChromaDB, which will store our FAQs in a vector database
chrom_client = chromadb.PersistentClient(path=r"data/vector_db/chromadb_faqs")

# Name for our collection of FAQs in the database
collection_name = "faqs_collection"

# (This is commented out) - Alternative embedding function that could be used
# ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Set up the Groq AI model using the model name from environment variables
groq_client = ChatGroq(model = os.environ['Groq_Model'])

# Set up a parser to extract plain text from AI responses
parser = StrOutputParser()

def ingest_faqs():
    """
    Load FAQs from CSV file into the vector database (only if not already loaded).
    This makes FAQs searchable using natural language queries.
    """
    # Check if the FAQ collection already exists in the database
    if collection_name not in [c.name for c in chrom_client.list_collections()]:
        print('Creating collection and ingesting FAQs...')
        
        # Create a new collection to store the FAQs
        collection = chrom_client.get_or_create_collection(name=collection_name,
                                                       # embedding_function=ef
                                                       )
    
        # Read the FAQ data from the CSV file
        df = pd.read_csv(faqs_path, encoding="utf-8")
        
        # Extract all questions as a list (these will be the searchable documents)
        doc = df['question'].tolist()
        
        # Create metadata for each question (includes the answer and topic)
        meta = [{"answer": df.loc[x, "answer"], "topic": df.loc[x, "topic"]}
                    for x in range(len(df))
                ]
        
        # Add all FAQs to the collection with unique IDs
        collection.add(
            documents=doc,  # The questions
            metadatas=meta,  # The answers and topics
            ids = [str(uuid.uuid4()) for _ in range(len(df))]  # Generate unique IDs
                        )
        print('Collection created and FAQs ingested successfully.')
        
    else:
        # If collection already exists, skip the loading process
        print('Collection already exists. Skipping ingestion.')

def get_relevant_qa(query):
    """
    Find the 3 most relevant FAQs based on the user's question.
    Uses vector similarity to match the query with stored questions.
    """
    # First, make sure the FAQs are loaded into the database
    ingest_faqs()
    
    # Get access to the FAQ collection
    collection = chrom_client.get_collection(name=collection_name)
    
    # Search for the 3 most similar questions to the user's query
    results = collection.query(
        query_texts=[query],  # The user's question
        n_results=3  # Get top 3 most relevant FAQs
    )
    
    # Return the search results (includes questions, answers, and topics)
    return results

def generate_faq_response(query, chat_history=[]):
    """
    Generate an AI response to the user's question using relevant FAQs and chat history.
    This is the main function that combines everything together.
    """
    # First, find the most relevant FAQs for this question
    result = get_relevant_qa(query)
    
    # Combine all the relevant answers into one context string
    context = ' '.join([r.get('answer') for r in result['metadatas'][0]])
    
    # Create a detailed prompt for the AI that includes:
    # - Instructions on how to behave (as a medical assistant)
    # - The conversation history (for context)
    # - The relevant FAQ answers (to provide accurate information)
    # - The user's current question
    prompt = f'''
                You are an expert medical assistant. 
                Never ever ask would you like help me like to help you or related.
                Just return the answer from the given context.
                Below is the conversation history and some relevant FAQs.
                Use them to answer the user's latest question.

                Conversation History:
                {chat_history}

                Relevant FAQs:
                {context}

                Question: {query}
            '''
    
    # Convert the prompt string into a LangChain PromptTemplate
    help_prompt = PromptTemplate(template = prompt)
    
    # Create a chain: prompt → AI model → parse output as string
    chain = help_prompt | groq_client | parser
    
    # Run the chain to get the AI's response
    result = chain.invoke({})
    
    # Return the final answer
    return result

    
# This code only runs if you execute this file directly (not when importing it)
if __name__ == "__main__":
    # Test the FAQ system with a sample question
    answer = generate_faq_response('Which documents required for addmission?')