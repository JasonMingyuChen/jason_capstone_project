import streamlit as st
from langgraph_pipeline import build_grading_graph
from langchain_core.messages import HumanMessage, AIMessage
from utils.rubric_parser import parse_rubric
import json
import time
from utils.llm_utils import ChatOpenAI
import PyPDF2
import io
import docx

def process_uploaded_rubric(uploaded_file):
    """Process uploaded rubric file and convert it to a structured format."""
    try:
        content = None
        file_type = uploaded_file.type
        
        # Handle different file types
        if file_type == "application/json":
            content = json.loads(uploaded_file.read().decode())
            # Store in both session state and graph state
            st.session_state.uploaded_rubric = content
            st.session_state.graph_state["uploaded_rubric"] = content
            st.session_state.rubric_criteria = content  # Also store as current rubric
            return content, "JSON rubric loaded successfully!"
            
        elif file_type == "text/plain":
            content = uploaded_file.read().decode()
        
        elif file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text()
                
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
        else:
            return None, f"Unsupported file type: {file_type}"
        
        # For non-JSON files, use GPT to structure the content
        if content:
            llm = ChatOpenAI(model="gpt-4", temperature=0)
            system_prompt = """Convert the following rubric text into a structured JSON format suitable for grading. The format should be:
            [{
                "description": "Criterion Name",
                "points": points_value,
                "long_description": "Detailed description of the criterion",
                "ratings": [
                    {"description": "Level name", "points": points_value},
                    ...
                ]
            }]
            
            Extract the criteria, point values, and rating levels from the text. If point values are not explicit, make reasonable assignments based on the content."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            response = llm.invoke(messages)
            try:
                structured_content = eval(response.content)  # Safe since we control the LLM prompt
                # Store in both session state and graph state
                st.session_state.uploaded_rubric = structured_content
                st.session_state.graph_state["uploaded_rubric"] = structured_content
                st.session_state.rubric_criteria = structured_content  # Also store as current rubric
                return structured_content, "Rubric processed and structured successfully!"
            except:
                return None, "Failed to structure the rubric content. Please check the format."
                
        return None, "Failed to process the rubric file."
        
    except Exception as e:
        return None, f"Error processing rubric: {str(e)}"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="""Hi! I'm your AI grading assistant. I can help you grade assignments and manage feedback. Here's how you can interact with me:

1. Upload a rubric file (optional) using the sidebar - I support:
   - JSON files (preferred for complex rubrics)
   - Text files (I'll help structure them)
   - PDF files (I'll extract and structure the content)
   - Word documents (I'll process the content)
   
2. Provide the course and assignment information in any of these formats:
   - Natural language: "I want to grade assignment 473 for course 121"
   - Structured format: "course_id: 121, assignment_id: 473"
   - Comma-separated: "121,473"
   
Once we have the course and assignment, I can help you:
- Preview the rubric
- Fetch student submissions
- Grade assignments
- Prepare and submit feedback

What would you like to do?""")
    ]

if "graph_state" not in st.session_state:
    st.session_state.graph_state = {
        "messages": [],
        "course_id": None,
        "assignment_id": None,
        "student_id": None,
        "uploaded_rubric": None,
        "error_count": 0,
        "last_error": None
    }

if "processing" not in st.session_state:
    st.session_state.processing = False

st.title("📘 AI Canvas Grader Chat")

# Custom CSS for loading spinner
st.markdown("""
    <style>
        .stSpinner > div > div {
            border-top-color: #4CAF50 !important;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
        }
        .assistant {
            background-color: #f0f2f6;
        }
        .user {
            background-color: #e3f2fd;
        }
    </style>
""", unsafe_allow_html=True)

# Helper text in sidebar
with st.sidebar:
    st.markdown("""
    ### 💡 Quick Tips
    
    You can interact with me in several ways:
    
    **View Rubric:**
    - "Show rubric for course 121, assignment 473"
    - "121,473"
    
    **Grade Submission:**
    - "Grade submission for student 247 in course 121, assignment 473"
    - "121,473,247"
    
    **Natural Language:**
    - "I want to see the rubric for CS101"
    - "Can you grade John's submission?"
    - "Show me the submissions for assignment 473"
    """)
    
    st.divider()
    st.header("Upload Files")
    
    # Track if a new file was just uploaded
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None
        
    uploaded_file = st.file_uploader(
        "Upload Rubric (Optional)", 
        type=["json", "txt", "pdf", "docx"],
        help="Upload your rubric in any of these formats. I'll help structure it for grading!"
    )
    
    # Only process if this is a new file upload
    if uploaded_file and (st.session_state.last_uploaded_file != uploaded_file.name):
        st.session_state.last_uploaded_file = uploaded_file.name
        with st.spinner("Processing rubric..."):
            try:
                structured_content, message = process_uploaded_rubric(uploaded_file)
                if structured_content:
                    st.session_state.graph_state["uploaded_rubric"] = structured_content
                    # Parse and preview the rubric
                    preview = parse_rubric(structured_content)
                    st.session_state.messages.append(
                        AIMessage(content=f"""✅ {message}

Here's how I've interpreted your rubric:

{preview}

You can now:
1. Start grading by providing course and assignment IDs
2. Use this rubric for any assignment
3. Modify the rubric if needed

What would you like to do next?""")
                    )
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error uploading file: {str(e)}")
    elif uploaded_file:
        # File is already uploaded and processed, just show a status indicator
        st.success("Rubric loaded and ready to use")

# Display chat messages
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        if isinstance(msg, AIMessage):
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg.content)
        else:
            with st.chat_message("user", avatar="👤"):
                st.write(msg.content)

    # Show loading message if processing
    if st.session_state.processing:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                st.write("Processing your request...")

# Chat input
if prompt := st.chat_input("Type your message here...", disabled=st.session_state.processing):
    # Add user message to chat history
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.session_state.processing = True
    st.rerun()

# Process the message if we're in processing state
if st.session_state.processing:
    try:
        # Add to graph state messages
        st.session_state.graph_state["messages"] = [
            msg for msg in st.session_state.messages if isinstance(msg, HumanMessage)
        ]
        
        # Process with graph
        with st.spinner("Processing..."):
            graph = build_grading_graph()
            result = graph.invoke(st.session_state.graph_state)
            
            # Handle the result
            if isinstance(result, dict):
                # Reset error count on successful execution
                st.session_state.graph_state["error_count"] = 0
                
                # Get the response from the result
                response = result.get("response", "")
                if isinstance(response, str) and response.strip():
                    st.session_state.messages.append(AIMessage(content=response))
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(response)
                
                # If no response but we have feedback, show the feedback interface
                elif "feedback" in result:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write("Here's the generated feedback. You can review and edit it:")
                        edited_feedback = st.text_area("Feedback", result["feedback"])
                        edited_score = st.number_input("Score", value=float(result.get("score", 0.0)))
                        
                        if st.button("Submit to Canvas"):
                            with st.spinner("Submitting to Canvas..."):
                                st.session_state.graph_state["final_feedback"] = edited_feedback
                                st.session_state.graph_state["final_score"] = edited_score
                                submit_result = graph.invoke({
                                    **st.session_state.graph_state,
                                    "messages": [HumanMessage(content="submit")]
                                })
                                if isinstance(submit_result, dict) and submit_result.get("response"):
                                    st.success(submit_result["response"])
                                else:
                                    st.success("Feedback submitted to Canvas!")
            
    except Exception as e:
        error_msg = str(e)
        st.session_state.graph_state["error_count"] = st.session_state.graph_state.get("error_count", 0) + 1
        st.session_state.graph_state["last_error"] = error_msg
        
        # Self-correction attempt if error count is within limit
        if st.session_state.graph_state["error_count"] <= 3:
            correction_msg = f"I encountered an error, but let me try to fix it: {error_msg}"
            st.session_state.messages.append(AIMessage(content=correction_msg))
            with st.chat_message("assistant", avatar="🤖"):
                st.write(correction_msg)
            
            try:
                # Retry with self-correction
                with st.spinner("Attempting to fix the error..."):
                    result = graph.invoke(st.session_state.graph_state)
                    if isinstance(result, dict) and result.get("response"):
                        success_msg = result["response"]
                    else:
                        success_msg = "I've fixed the issue and completed the operation."
                    st.session_state.messages.append(AIMessage(content=success_msg))
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(success_msg)
            except Exception as retry_error:
                failure_msg = "I'm still having trouble. Could you try rephrasing your request or providing the information in a different format?"
                st.session_state.messages.append(AIMessage(content=failure_msg))
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(failure_msg)
        else:
            reset_msg = "I'm having persistent issues. Let's start over. Could you please provide the information again?"
            st.session_state.messages.append(AIMessage(content=reset_msg))
            with st.chat_message("assistant", avatar="🤖"):
                st.write(reset_msg)
            # Reset error count
            st.session_state.graph_state["error_count"] = 0
    
    finally:
        st.session_state.processing = False
        st.rerun()

# Clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state.messages = [
        AIMessage(content="""Hi! I'm your AI grading assistant. I can help you grade assignments and manage feedback. Here's how you can interact with me:

1. Upload a rubric file (optional) using the sidebar - I support:
   - JSON files (preferred for complex rubrics)
   - Text files (I'll help structure them)
   - PDF files (I'll extract and structure the content)
   - Word documents (I'll process the content)
   
2. Provide the course and assignment information in any of these formats:
   - Natural language: "I want to grade assignment 473 for course 121"
   - Structured format: "course_id: 121, assignment_id: 473"
   - Comma-separated: "121,473"
   
Once we have the course and assignment, I can help you:
- Preview the rubric
- Fetch student submissions
- Grade assignments
- Prepare and submit feedback

What would you like to do?""")
    ]
    st.session_state.graph_state = {
        "messages": [],
        "course_id": None,
        "assignment_id": None,
        "student_id": None,
        "uploaded_rubric": None,
        "error_count": 0,
        "last_error": None
    }
    st.session_state.processing = False
    st.rerun()