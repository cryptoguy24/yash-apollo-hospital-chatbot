import streamlit as st
from router import router
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from faq import generate_faq_response
from sql import handling_agent
from dotenv import load_dotenv
import uuid
import os
import time

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

# --- LLM SETUP ---
template = """
You are a helpful assistant from Apollo Hospital. 
Greet the user warmly if they greet you. 

The user asked: {query}

This question seems unrelated to Apollo Hospital. 
Politely explain that you can only assist with hospital-related 
queries like appointments, doctors, and services.
"""
llm = ChatGroq(model=os.environ.get('GROQ_MODEL_L1', 'llama3-8b-8192')) 
helping_prompt = PromptTemplate(template=template, input_variables=["query"])
parser = StrOutputParser()
chain = helping_prompt | llm | parser

# --- UTILITY: STREAMING HELPERS ---
def text_to_stream(text: str):
    """Yields text word by word for the typewriter effect."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02) # Faster streaming speed

def response_generator(response_obj):
    """Processes either a LangChain stream or a raw string."""
    if isinstance(response_obj, str):
        yield from text_to_stream(response_obj)
    else:
        for chunk in response_obj:
            if hasattr(chunk, 'content'):
                yield chunk.content
            else:
                yield chunk

# --- CORE LOGIC ---
def ask(query: str, session_id: str):
    # Minimal thinking status without the "Identifying request" line
    with st.status("🏥 Apollo Assistant is thinking...", expanded=False) as status:
        route = router(query)
        
        if route.name == "faq":
            st.session_state.last_active_route = "faq"
            res = generate_faq_response(query)
            status.update(label="Found in FAQ", state="complete")
            return res

        elif route.name == "appointment":
            st.session_state.last_active_route = "appointment"
            res = handling_agent(query, session_id)
            status.update(label="Checking appointments...", state="complete")
            return res

        else:
            # Handle context-based follow-ups
            if st.session_state.last_active_route == "appointment":
                return handling_agent(query, session_id)
            
            elif st.session_state.last_active_route == "faq":
                history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                return generate_faq_response(query, chat_history=history_context)
            
            else:
                # Fallback to polite refusal/greeting (returns a LangChain stream)
                status.update(label="Ready", state="complete")
                return chain.stream({'query': query})

# --- CALLBACK FOR SIDEBAR BUTTONS ---
def handle_quick_query(query_text):
    st.session_state.messages.append({"role": "user", "content": query_text})
    st.rerun()

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("Patient Portal")
    st.markdown("### ⚡ Quick Actions")
    if st.button("🔍 Find Doctor Available Today", use_container_width=True):
        handle_quick_query("Which doctors are available today?")
    if st.button("📅 Book an Appointment", use_container_width=True):
        handle_quick_query("I want to book an appointment.")
    st.divider()
    if st.button("🗑️ Clear Chat History", type="secondary"):
        st.session_state.messages = []
        st.session_state.last_active_route = None
        st.rerun()

# --- MAIN CHAT UI ---
st.title("🏥 Apollo Hospital AI Assistant")

# Display historical messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle User Input
query = st.chat_input("Ask about specialized care, or hospital FAQs...")

if query or (len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user"):
    if query:
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.messages.append({"role": "user", "content": query})
    else:
        query = st.session_state.messages[-1]["content"]

    # Assistant Response
    with st.chat_message("assistant"):
        response_obj = ask(query, st.session_state.session_id)
        # Streams the response word by word
        full_response = st.write_stream(response_generator(response_obj))
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})