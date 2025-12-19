# -----------------------------
# Importing Required Libraries
# -----------------------------
import streamlit as st
from router import router
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

# --- CUSTOM CSS FOR BRANDING ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    .st-emotion-cache-1c7n2ka { 
        background-color: #ffffff; /* Background for chat messages */
        border: 1px solid #dee2e6;
        border-radius: 10px;
    }
    h1 {
        color: #004a99; /* Apollo Blue */
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

load_dotenv()

# -----------------------------
# Session Management
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
if "last_active_route" not in st.session_state:
    st.session_state.last_active_route = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR UI ---
with st.sidebar:
    st.image("https://www.apollohospitals.com/wp-content/themes/apollohospitals/assets/images/logo.png", width=200)
    st.title("Patient Portal")
    st.info("Welcome to Apollo's AI Assistant. You can book appointments or ask about our services.")
    
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.last_active_route = None
        st.rerun()
    
    st.divider()
    st.markdown("### Quick Links")
    st.markdown("- [Emergency Services](https://www.apollohospitals.com)")
    st.markdown("- [Find a Doctor](https://www.apollohospitals.com)")

# -----------------------------
# Core logic function
# -----------------------------
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
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            return generate_faq_response(query, chat_history=history_context)
        
        else:
            return "Please ask only about Apollo Hospital related queries."

# -----------------------------
# Streamlit UI Construction
# -----------------------------
st.title("🏥 Apollo Hospital AI Assistant")
st.caption("How can we help you stay healthy today?")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new input
query = st.chat_input("Ask me about appointments, specialized care, or hospital FAQs...")

if query:
    # User message
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})

    # Bot response
    with st.spinner("Consulting hospital records..."):
        response = ask(query, st.session_state.session_id)

    # Display Assistant message
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
