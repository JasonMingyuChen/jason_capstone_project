from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

def strict_grading_llm(submission: str, rubric: str) -> dict:
    """
    Returns a configured LLMChain for grading with a stricter evaluation prompt.
    
    Args:
        submission (str): The student's submission text
        rubric (str): The formatted rubric text
        
    Returns:
        dict: Contains score and detailed feedback
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are a strict but fair grading assistant. Your task is to:\n"
         "1. Grade the submission exactly according to the provided rubric structure\n"
         "2. For each criterion in the rubric:\n"
         "   - Provide the criterion name and points awarded\n"
         "   - Break down sub-criteria points if specified\n"
         "   - Give specific feedback explaining the score\n"
         "3. Ensure point allocations match the rubric exactly\n"
         "4. Sum up the total score accurately\n"
         "5. Provide a summary of strengths and areas for improvement\n\n"
         "Format your response as:\n"
         "Overall Score: [total]/[maximum]\n\n"
         "[For each criterion:]\n"
         "Criterion Name: [points awarded]/[total points]\n"
         "[Sub-criteria breakdown if any]\n"
         "Feedback: [specific feedback]\n\n"
         "[After all criteria:]\n"
         "Strengths: [summary of strong points]\n"
         "Areas for Improvement: [specific suggestions]\n\n"
         "IMPORTANT: Follow the exact point structure and criteria names from the provided rubric."),
        ("human", 
         "Rubric:\n{rubric}\n\n"
         "Submission:\n{submission}\n\n"
         "Please provide a detailed evaluation following the format specified.")
    ])
    
    chain = LLMChain(
        llm=ChatOpenAI(model="gpt-4", temperature=0.3),
        prompt=prompt
    )
    
    # Run the chain
    result = chain.run({
        "rubric": rubric,
        "submission": submission
    })
    
    # Extract score and format feedback
    try:
        # Try to parse the score from the first line
        first_line = result.split('\n')[0]
        if 'Score:' in first_line or 'Overall Score:' in first_line:
            score = float(first_line.split(':')[1].split('/')[0].strip())
        else:
            # If not in first line, try to sum up individual criterion scores
            score = 0
            lines = result.split('\n')
            for line in lines:
                if ':' in line and '/' in line:
                    try:
                        score_part = line.split(':')[1].split('/')[0].strip()
                        score += float(score_part)
                    except:
                        continue
    except:
        score = 0  # Default score if parsing fails
        
    return {
        "score": score,
        "feedback": result
    }