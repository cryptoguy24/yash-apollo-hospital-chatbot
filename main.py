import streamlit as st
from router import router
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import GROQ_MODEL_L2
from faq import generate_faq_response
from sql import handling_agent
from dotenv import load_dotenv
import uuid
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Apollo Hospital Assistant",
    page_icon="🏥",
    layout="centered"
)

load_dotenv()

# --- SESSION MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "last_active_route" not in st.session_state:
    st.session_state.last_active_route = None
if "messages" not in st.session_state:
    st.session_state.messages = []
    
# --- llm_client ---
template = """
You are a helpful assistant from Apollo Hospital. 
You greet the user warmly if they greet you. 

The user asked: {query}

This question seems unrelated to Apollo Hospital. 
Politely explain that you can only assist with hospital-related 
queries like appointments, doctors, and services.
"""
llm = ChatGroq(model=os.environ.get('GROQ_MODEL_L1')) # Using a fast model for refusals
helping_prompt = PromptTemplate(template=template, input_variables=["query"])
parser = StrOutputParser()
chain = helping_prompt | llm | parser

# --- CORE LOGIC ---
def ask(query: str, session_id: str) -> str:
    route = router(query)
    if route.name == "faq":
        st.session_state.last_active_route = "faq"
        return generate_faq_response(query)
    elif route.name == "appointment":
        st.session_state.last_active_route = "appointment"
        return handling_agent(query, session_id)
    else:
        if st.session_state.last_active_route == "appointment":
            return handling_agent(query, session_id)
        elif st.session_state.last_active_route == "faq":
            # Pass history for context
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            return generate_faq_response(query, chat_history=history_context)
        else:
            return chain.invoke({'query':query}) #"Please ask only about Apollo Hospital related queries."

# --- CALLBACK FOR BUTTONS ---
def handle_quick_query(query_text):
    """Simulates a user typing and submitting a query"""
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": query_text})
    # 2. Get and Add Bot Response
    response = ask(query_text, st.session_state.session_id)
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("Patient Portal")
    
    st.markdown("### ⚡ Quick Actions")
    # Button 1: Find Doctor
    if st.button("🔍 Find Doctor Available Today", use_container_width=True):
        handle_quick_query("Which doctors are available today?")
    
    # Button 2: Book Appointment
    if st.button("📅 Book an Appointment", use_container_width=True):
        handle_quick_query("I want to book an appointment.")
        
    st.divider()
    if st.button("🗑️ Clear Chat History", type="secondary"):
        st.session_state.messages = []
        st.session_state.last_active_route = None
        st.rerun()

# --- CHAT UI ---
st.title("🏥 Apollo Hospital AI Assistant")
st.caption("Real-time help with doctors and hospital services")



# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle manual text input
query = st.chat_input("Ask me about specialized care, or hospital FAQs...")

if query:
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("Searching records..."):
        response = ask(query, st.session_state.session_id)

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
