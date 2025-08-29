# langgraph_pipeline.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
import re
import streamlit as st

from tool.rubric_tool import preview_rubric_tool, load_rubric_tool
from tool.submission_tool import fetch_submission_tool
from tool.grading_tool import (
    grade_selected_tool,
    modify_grade_tool,
    modify_feedback_tool,
    submit_to_canvas_tool,
    show_feedback_tool
)
from tool.feedback_tool import submit_feedback_tool
from tool.submit_tool import submit_tool
from dataclasses import dataclass, field
from typing import List, Union, Dict, Any, Optional, Tuple
from langchain_core.messages import BaseMessage

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
)

# Internal state storage for non-Streamlit environments
_internal_state = {}

def get_state_store():
    """Get the appropriate state store based on environment."""
    try:
        if st._is_running_with_streamlit:
            return st.session_state
    except:
        pass
    return _internal_state

@dataclass
class GradingState:
    messages: List[BaseMessage] = field(default_factory=list)
    error_count: int = 0
    last_error: str = None
    course_id: Optional[str] = None
    assignment_id: Optional[str] = None
    student_id: Optional[str] = None
    uploaded_rubric: Optional[str] = None
    next: Optional[str] = None
    response: Optional[str] = None
    current_grade: Optional[float] = None
    current_feedback: Optional[str] = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value with a default if not found."""
        # First check state store
        state_store = get_state_store()
        if key in state_store:
            return state_store[key]
        # Then check instance attributes
        return getattr(self, key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Enable dictionary-style assignment."""
        # Store in both state store and instance
        state_store = get_state_store()
        state_store[key] = value
        setattr(self, key, value)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple attributes at once."""
        for key, value in data.items():
            self[key] = value
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        # Get values from state store if available
        state_dict = {
            "messages": self.messages,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "course_id": self.get("course_id"),
            "assignment_id": self.get("assignment_id"),
            "student_id": self.get("student_id"),
            "uploaded_rubric": self.get("uploaded_rubric"),
            "next": self.next,
            "response": self.response,
            "current_grade": self.get("current_grade"),
            "current_feedback": self.get("current_feedback")
        }
        return state_dict

    def persist_grading_state(self) -> None:
        """Ensure grading state is persisted in state store."""
        state_store = get_state_store()
        state_store["course_id"] = self.course_id
        state_store["assignment_id"] = self.assignment_id
        state_store["student_id"] = self.student_id
        if self.current_grade is not None:
            state_store["current_grade"] = self.current_grade
        if self.current_feedback is not None:
            state_store["current_feedback"] = self.current_feedback

def understand_user_intent(message: str) -> Tuple[str, Dict[str, Any]]:
    """Use LLM to understand user intent and extract relevant information."""
    print(f"Processing message: {message}")
    
    # Check for grade modification commands first
    message_lower = message.lower()
    
    # Handle feedback modification (both formats)
    if "feedback:" in message_lower:
        feedback = message.split("feedback:", 1)[1].strip()
        return "modify_feedback", {"feedback": feedback}
    elif "modify grade feedback:" in message_lower:
        feedback = message.split("modify grade feedback:", 1)[1].strip()
        return "modify_feedback", {"feedback": feedback}
    
    # Handle score modification
    if "modify grade" in message_lower and "score:" in message_lower:
        try:
            score = float(message_lower.split("score:")[1].strip())
            return "modify_grade", {"score": score}
        except:
            pass
    
    # Check for grade submission command
    if "submit grade to canvas" in message_lower:
        return "submit_grade", {}
    
    # First try to parse comma-separated format (e.g., "121,473")
    if "," in message and not any(word in message.lower() for word in ["course", "assignment", "student"]):
        parts = [part.strip() for part in message.split(",")]
        if len(parts) == 2:
            result = ("view_rubric", {"course_id": parts[0], "assignment_id": parts[1]})
            print(f"Parsed comma format: {result}")
            return result
        elif len(parts) == 3:
            result = ("fetch_submission", {"course_id": parts[0], "assignment_id": parts[1], "student_id": parts[2]})
            print(f"Parsed comma format: {result}")
            return result
    
    # Then try to parse structured format (e.g., "course_id: 121, assignment_id: 473")
    structured_match = re.findall(r'(\w+)_id:\s*(\d+)', message)
    if structured_match:
        entities = {key: value for key, value in structured_match}
        if "course" in entities and "assignment" in entities:
            result = ("view_rubric", entities)
            print(f"Parsed structured format: {result}")
            return result
        if "student" in entities:
            result = ("fetch_submission", entities)
            print(f"Parsed structured format: {result}")
            return result
    
    # Finally, use LLM for natural language understanding
    system_prompt = """You are an AI that understands user requests about grading assignments.
Extract the intent and any relevant IDs from the user's message.
Respond in JSON format with two fields:
1. "intent": One of [view_rubric, load_rubric, fetch_submission, grade_submission, prepare_feedback, submit_feedback, modify_grade, submit_grade, show_feedback, unknown]
2. "entities": Dictionary containing any found course_id, assignment_id, student_id, score, or feedback

Example inputs and outputs:
"Show rubric for course 121 assignment 473"
{"intent": "view_rubric", "entities": {"course_id": "121", "assignment_id": "473"}}

"Grade submission for student 247 in course 121, assignment 473"
{"intent": "grade_submission", "entities": {"course_id": "121", "assignment_id": "473", "student_id": "247"}}

"modify grade score: 98"
{"intent": "modify_grade", "entities": {"score": 98}}

"modify feedback: good job"
{"intent": "modify_grade", "entities": {"feedback": "good job"}}

"show feedback"
{"intent": "show_feedback", "entities": {}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    try:
        response = llm.invoke(messages)
        print(f"LLM response: {response.content}")
        result = eval(response.content)  # Safe since we control the LLM prompt
        print(f"Parsed LLM result: {result}")
        return result["intent"], result["entities"]
    except Exception as e:
        print(f"Error in LLM parsing: {str(e)}")
        return "unknown", {}

def generate_response(intent: str, state: GradingState, success: bool = True) -> str:
    """Use LLM to generate a natural language response."""
    context = {
        "intent": intent,
        "course_id": state.course_id,
        "assignment_id": state.assignment_id,
        "student_id": state.student_id,
        "success": success,
        "error": state.last_error
    }
    
    system_prompt = """You are a helpful AI grading assistant.
Generate a natural response based on the context provided.
Keep responses concise but friendly and informative.
If there's an error, explain what information is needed."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": str(context)}
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception:
        return "I understand your request. Let me help you with that."

def user_input_router(state: GradingState) -> Dict[str, Any]:
    """Route user input to appropriate tools based on message content and context."""
    if not state.messages:
        return {"next": END}
    
    last_message = state.messages[-1].content
    print(f"\nCurrent state before processing: course_id={state.get('course_id')}, assignment_id={state.get('assignment_id')}, student_id={state.get('student_id')}")
    print(f"Processing message in router: {last_message}")
    
    # Use LLM to understand intent
    intent, entities = understand_user_intent(last_message)
    print(f"Understood intent: {intent}")
    print(f"Extracted entities: {entities}")
    
    # Update state with extracted entities
    if entities:
        state.update(entities)
        print(f"Updated state: course_id={state.get('course_id')}, assignment_id={state.get('assignment_id')}, student_id={state.get('student_id')}")
    
    # Get state dictionary for passing to next node
    state_dict = state.to_dict()
    
    # Handle grade or feedback modification
    if intent in ["modify_grade", "modify_feedback"]:
        if not all([state.get('course_id'), state.get('assignment_id'), state.get('student_id')]):
            # Check if we have a current grade or feedback to modify
            if intent == "modify_grade" and state.get('current_grade') is None:
                print("Missing required fields and no current grade")
                response = "Please grade a submission first before trying to modify the grade."
                state_dict["response"] = response
                state_dict["next"] = END
                return state_dict
            elif intent == "modify_feedback" and not state.get('current_feedback') and not state.get('current_grade'):
                print("Missing required fields and no current feedback")
                response = "Please grade a submission first before trying to modify the feedback."
                state_dict["response"] = response
                state_dict["next"] = END
                return state_dict
        
        print(f"Proceeding with {intent}")
        state_dict["next"] = intent
        return state_dict
    
    # Handle grade submission to Canvas
    if intent == "submit_grade":
        if not all([state.get('course_id'), state.get('assignment_id'), state.get('student_id')]):
            print("Missing required fields for grade submission")
            response = "Please grade a submission first before trying to submit to Canvas."
            state_dict["response"] = response
            state_dict["next"] = END
            return state_dict
        print("Proceeding with grade submission to Canvas")
        state_dict["next"] = "submit_grade"
        return state_dict
    
    # Handle grading submission
    if intent == "grade_submission":
        # Ensure we persist the state
        state.persist_grading_state()
        print(f"Proceeding with grade_submission: course_id={state.get('course_id')}, assignment_id={state.get('assignment_id')}, student_id={state.get('student_id')}")
        state_dict["next"] = "grade_submission"
        return state_dict
    
    # Generate appropriate response based on intent and available information
    if intent == "view_rubric":
        if not state.get('course_id') or not state.get('assignment_id'):
            print(f"Missing required fields for view_rubric: course_id={state.get('course_id')}, assignment_id={state.get('assignment_id')}")
            response = generate_response(intent, state, False)
            state_dict["response"] = response
            state_dict["next"] = END
            return state_dict
        print(f"Proceeding with view_rubric: course_id={state.get('course_id')}, assignment_id={state.get('assignment_id')}")
        state_dict["next"] = "preview_rubric"
        return state_dict
    
    elif intent == "load_rubric":
        state_dict["next"] = "load_rubric"
        return state_dict
    
    elif intent == "fetch_submission":
        if not all([state.get('course_id'), state.get('assignment_id'), state.get('student_id')]):
            print(f"Missing required fields for fetch_submission")
            response = generate_response(intent, state, False)
            state_dict["response"] = response
            state_dict["next"] = END
            return state_dict
        state_dict["next"] = "fetch_submission"
        return state_dict
    
    # Handle unknown intent or missing information
    print("Unknown intent or missing information")
    response = generate_response("unknown", state, False)
    state_dict["response"] = response
    state_dict["next"] = END
    return state_dict

def build_grading_graph():
    # Build the LangGraph
    builder = StateGraph(GradingState)
    
    # Create tool nodes with proper input formatting
    def format_tool_input(state: Dict[str, Any], tool_name: str) -> str:
        """Format the input for tools based on the state."""
        print(f"Formatting input for {tool_name} with state: {state}")
        
        if isinstance(state, GradingState):
            # If state is a GradingState object, use its get method
            get_value = state.get
        else:
            # If state is a dict, use dict.get
            get_value = state.get
        
        if tool_name == "modify_grade":
            # Handle score modification
            score = get_value("score")
            if score is not None:
                return f"score: {score}"
            
            # Handle feedback modification
            feedback = get_value("feedback")
            if feedback is not None:
                return f"feedback: {feedback}"
            
            return ""
            
        elif tool_name == "modify_feedback":
            # Handle feedback modification
            feedback = get_value("feedback")
            if feedback is not None:
                return feedback
            return ""
            
        elif tool_name == "preview_rubric":
            course_id = get_value("course_id")
            assignment_id = get_value("assignment_id")
            if not course_id or not assignment_id:
                print("Warning: Missing required fields for preview_rubric")
                return ""
            formatted = f"{course_id},{assignment_id}"
            print(f"Formatted input: {formatted}")
            return formatted
            
        elif tool_name == "fetch_submission":
            course_id = get_value("course_id")
            assignment_id = get_value("assignment_id")
            student_id = get_value("student_id")
            if not all([course_id, assignment_id, student_id]):
                print("Warning: Missing required fields for fetch_submission")
                return ""
            formatted = f"{course_id},{assignment_id},{student_id}"
            print(f"Formatted input: {formatted}")
            return formatted
            
        elif tool_name == "grade_submission":
            course_id = get_value("course_id")
            assignment_id = get_value("assignment_id")
            student_id = get_value("student_id")
            if not all([course_id, assignment_id, student_id]):
                print("Warning: Missing required fields for grade_submission")
                return ""
            formatted = f"{course_id},{assignment_id},{student_id}"
            print(f"Formatted input: {formatted}")
            return formatted
            
        elif tool_name == "submit_grade":
            return ""  # No input needed, uses session state
            
        return ""
    
    def create_tool_node(tool, name: str):
        def tool_with_state(state: GradingState) -> Dict[str, Any]:
            try:
                # Format input based on tool requirements
                tool_input = format_tool_input(state, name)
                print(f"Executing {name} with input: {tool_input}")
                
                # Execute tool
                result = tool(tool_input)
                print(f"Tool result: {result}")
                
                # Update state with result
                state_dict = state.to_dict()
                state_dict["response"] = result
                state_dict["next"] = END
                
                return state_dict
            except Exception as e:
                print(f"Error in {name}: {str(e)}")
                state_dict = state.to_dict()
                state_dict["error_count"] = state.error_count + 1
                state_dict["last_error"] = str(e)
                state_dict["response"] = f"Error in {name}: {str(e)}"
                state_dict["next"] = END
                return state_dict
        
        return RunnableLambda(tool_with_state)
    
    # Add nodes to graph
    builder.add_node("router", RunnableLambda(user_input_router))
    builder.add_node("preview_rubric", create_tool_node(preview_rubric_tool, "preview_rubric"))
    builder.add_node("load_rubric", create_tool_node(load_rubric_tool, "load_rubric"))
    builder.add_node("fetch_submission", create_tool_node(fetch_submission_tool, "fetch_submission"))
    builder.add_node("grade_submission", create_tool_node(grade_selected_tool, "grade_submission"))
    builder.add_node("modify_grade", create_tool_node(modify_grade_tool, "modify_grade"))
    builder.add_node("modify_feedback", create_tool_node(modify_feedback_tool, "modify_feedback"))
    builder.add_node("submit_grade", create_tool_node(submit_to_canvas_tool, "submit_grade"))
    
    # Add edges
    builder.set_entry_point("router")
    
    def conditional_edge_handler(state_dict: Dict[str, Any]) -> str:
        """Handle edges based on state."""
        return state_dict.get("next", END)
    
    # Connect router to all possible next nodes
    builder.add_conditional_edges(
        "router",
        conditional_edge_handler,
        {
            "preview_rubric": "preview_rubric",
            "load_rubric": "load_rubric",
            "fetch_submission": "fetch_submission",
            "grade_submission": "grade_submission",
            "modify_grade": "modify_grade",
            "modify_feedback": "modify_feedback",
            "submit_grade": "submit_grade",
            END: END
        }
    )
    
    # Connect all tool nodes to END
    for node in ["preview_rubric", "load_rubric", "fetch_submission", "grade_submission", "modify_grade", "modify_feedback", "submit_grade"]:
        builder.add_edge(node, END)
    
    return builder.compile()