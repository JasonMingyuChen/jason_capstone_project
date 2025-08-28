import os
import streamlit as st
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from autograde_tool import auto_grade_and_submit_tool

# API key check
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not set in secrets or environment.")
    st.stop()
os.environ["OPENAI_API_KEY"] = api_key

# Streamlit UI setup
st.set_page_config(page_title="📘 Auto Grader", layout="centered")
st.title("📘 Canvas Auto Grader")

st.markdown(
    """
    🔹 **Instructions**  
    Please enter:  
    `course_id, assignment_id, student_id`  
    Example: `121,424,789`
    """
)

# Memory and tool setup
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
llm = ChatOpenAI(model="gpt-4", temperature=0.3)

tools = [auto_grade_and_submit_tool]
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    memory=memory,
    verbose=False,
)

# Input handling
user_input = st.chat_input("Enter grading request...")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if user_input:
    st.session_state.chat_history.append(("user", user_input))

    try:
        with st.spinner("Grading in progress..."):
            result = auto_grade_and_submit_tool.invoke(user_input)
    except Exception as e:
        result = f" Error: {str(e)}"

    st.session_state.chat_history.append(("ai", result))

# Display chat history
for role, msg in st.session_state.chat_history:
    st.chat_message("user" if role == "user" else "assistant").write(msg)
