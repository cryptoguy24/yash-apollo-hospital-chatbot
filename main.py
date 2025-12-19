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

load_dotenv()

# -----------------------------
# Session Management
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
if "last_active_route" not in st.session_state:
    st.session_state.last_active_route = None
# -----------------------------
# Core logic function
# -----------------------------

def ask(query: str, session_id: str) -> str:
    route = router(query)

    # -------------------------------------------
    # SCENARIO A: Router found a Clear Match
    # -------------------------------------------
    if route.name == "faq":
        st.session_state.last_active_route = "faq"  # Update memory
        return generate_faq_response(query)

    elif route.name == "appointment":
        st.session_state.last_active_route = "appointment" # Update memory
        return handling_agent(query, session_id)
    
    # -------------------------------------------
    # SCENARIO B: Router is Unsure (e.g., "Yes", "10 AM", "Confirm")
    # -------------------------------------------
    else:
        # Check if we were previously in the middle of a booking flow
        if st.session_state.last_active_route == "appointment":
            # Assume this is a follow-up answer for the agent
            return handling_agent(query, session_id)
        
        elif route.name == "faq":
            st.session_state.last_active_route = "faq"
            # Convert session_state messages to a formatted string for the FAQ prompt
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            return generate_faq_response(query, chat_history=history_context)
        
        else:
            return "Please ask only about Apollo Hospital related queries."
# -----------------------------
# Streamlit UI
# -----------------------------
st.title("Apollo Hospital Chatbot")

query = st.chat_input("Ask me anything about Apollo Hospital:")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new input
if query:
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    # Bot response
    response = ask(query, st.session_state.session_id)

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )