import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage
import uuid
from datetime import datetime

# **************************************** utility functions *************************

def generate_thread_id():
    """Generate a unique thread ID for conversation tracking"""
    return str(uuid.uuid4())

def reset_chat():
    """Initialize a new chat thread and reset message history"""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['message_history'] = []
    st.rerun()  # Refresh the interface

def add_thread(thread_id):
    """Add a new thread to the chat threads list with metadata"""
    if thread_id not in [t['id'] for t in st.session_state['chat_threads']]:
        thread_data = {
            'id': thread_id,
            'created_at': datetime.now(),
            'title': 'New Chat'  # Will be updated with first message
        }
        st.session_state['chat_threads'].append(thread_data)

def load_conversation(thread_id):
    """Load conversation messages from LangGraph state"""
    try:
        messages = chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values['messages']
        return messages
    except Exception as e:
        st.error(f"Error loading conversation: {str(e)}")
        return []

def update_thread_title(thread_id, first_message):
    """Update thread title based on first message"""
    for thread in st.session_state['chat_threads']:
        if thread['id'] == thread_id:
            # Use first 30 characters of the message as title
            thread['title'] = first_message[:30] + "..." if len(first_message) > 30 else first_message
            break

def delete_thread(thread_id):
    """Delete a conversation thread"""
    st.session_state['chat_threads'] = [t for t in st.session_state['chat_threads'] if t['id'] != thread_id]
    if st.session_state.get('thread_id') == thread_id:
        reset_chat()

def format_timestamp(dt):
    """Format datetime for display"""
    return dt.strftime("%m/%d %H:%M")

# **************************************** Session Setup ******************************

# Initialize session state variables
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

# Add current thread if not exists
add_thread(st.session_state['thread_id'])

# **************************************** Sidebar UI *********************************

st.sidebar.title('🤖 LangGraph Chatbot')

# New chat button
if st.sidebar.button('➕ New Chat', use_container_width=True):
    reset_chat()

st.sidebar.markdown("---")
st.sidebar.header('💬 My Conversations')

# Display conversation threads with better formatting
if st.session_state['chat_threads']:
    for thread in sorted(st.session_state['chat_threads'], key=lambda x: x['created_at'], reverse=True):
        thread_id = thread['id']
        title = thread['title']
        created_at = thread['created_at']
        
        # Create columns for thread button and delete button
        col1, col2 = st.sidebar.columns([4, 1])
        
        with col1:
            # Highlight current thread
            if thread_id == st.session_state['thread_id']:
                if st.button(f"🟢 {title}", key=f"thread_{thread_id}", use_container_width=True):
                    pass  # Already selected
            else:
                if st.button(f"⚪ {title}", key=f"thread_{thread_id}", use_container_width=True):
                    st.session_state['thread_id'] = thread_id
                    messages = load_conversation(thread_id)
                    
                    temp_messages = []
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            role = 'user'
                        else:
                            role = 'assistant'
                        temp_messages.append({'role': role, 'content': msg.content})
                    
                    st.session_state['message_history'] = temp_messages
                    st.rerun()
        
        with col2:
            if st.button("🗑️", key=f"delete_{thread_id}", help="Delete conversation"):
                delete_thread(thread_id)
                st.rerun()
        
        # Show timestamp
        st.sidebar.caption(format_timestamp(created_at))
        st.sidebar.markdown("---")
else:
    st.sidebar.write("No conversations yet. Start a new chat!")

# **************************************** Main UI ************************************

st.title("🤖 LangGraph Assistant")
st.caption("Powered by LangGraph • Streaming responses enabled")

# Add some spacing
st.markdown("<br>", unsafe_allow_html=True)

# Display conversation history with better formatting
if st.session_state['message_history']:
    for message in st.session_state['message_history']:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
else:
    # Welcome message for new chats
    st.markdown("""
    <div style="text-align: center; padding: 50px; color: #666;">
        <h3>👋 Welcome to LangGraph Chat!</h3>
        <p>Start a conversation by typing your message below.</p>
    </div>
    """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input('Type your message here...')

if user_input:
    # Update thread title if this is the first message
    if not st.session_state['message_history']:
        update_thread_title(st.session_state['thread_id'], user_input)
    
    # Add user message to history and display
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # Configuration for LangGraph
    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

    # Generate and stream assistant response
    with st.chat_message('assistant'):
        try:
            # Create a placeholder for the streaming response
            response_placeholder = st.empty()
            full_response = ""
            
            # Stream the response
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            ):
                if hasattr(message_chunk, 'content') and message_chunk.content:
                    full_response += message_chunk.content
                    response_placeholder.markdown(full_response + "▌")  # Add cursor effect
            
            # Remove cursor and show final response
            response_placeholder.markdown(full_response)
            
            # Add assistant response to history
            st.session_state['message_history'].append({'role': 'assistant', 'content': full_response})
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.error(error_msg)
            st.session_state['message_history'].append({'role': 'assistant', 'content': error_msg})

# Add footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "💡 Tip: Use the sidebar to manage multiple conversations"
    "</div>", 
    unsafe_allow_html=True
)