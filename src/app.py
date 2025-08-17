from workflow.graph import WorkFlow
from fastapi import FastAPI, BackgroundTasks, HTTPException
import os
import logging
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utlis.format_plan import format_plans_to_markdown
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
current_dir = os.path.dirname(os.path.abspath(__file__))
# List of allowed origins (for example, frontend URLs)
origins = [
    "*",
]

class ChatRequest(BaseModel):
    query: str
    codebase: list
    workspace_id: str
    session_id: str
    sa_key_bucket_link: str
class ChatBackgroundResponse(BaseModel):
    agent_response: str
    plan: str
    status: str
    message: str
    agent_trajectory: str
    input_tokens: int
    output_tokens: int

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Origins that are allowed to make requests
    allow_credentials=True,
    allow_methods=["*"],              # Allow all HTTP methods: GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],              # Allow all headers
)

@app.get("/health")
def health_check():
    """Health check endpoint for the DevOps agent API."""
    return {"status": "healthy", "message": "DevOps agent API is running"}


@app.get("/")
def root():
    """Root endpoint that redirects to docs."""
    return {"message": "DevOps Agent API", "docs": "/docs"}


@app.post("/chat", response_model=ChatBackgroundResponse)
def chat(request: ChatRequest):
    try:
        local_base = os.path.abspath(os.path.join(current_dir, "tmp", request.session_id, "codebase"))
        os.makedirs(local_base, exist_ok=True)
        logger.info("Workflow endpoint called")
        work_flow = WorkFlow(request=request)
        work_flow(request=request)
        
        # Log workflow state
        work_flow.show_state()
        
        agent_trajectory=work_flow.messages_to_trajectory_string()
        state_values = work_flow.workflow.get_state(work_flow.config).values
        logger.info(f"Input tokens used: {state_values.get('input_tokens',0)}, Output tokens used: {state_values.get('output_tokens',0)}")
        return {
            "agent_response": state_values.get("agent_response",""),
            "plan":format_plans_to_markdown(state_values.get("plans", [])),
            "status": "success",
            "message": "devops agent launched successfully.",
            "agent_trajectory":agent_trajectory,
            "input_tokens":state_values.get("input_tokens",0),
            "output_tokens":state_values.get("output_tokens",0)
        }
        
    except Exception as e:
        logger.error(f"Error launching workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to launch workflow: {str(e)}"
        )