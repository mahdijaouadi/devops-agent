import os
import subprocess
import json
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

current_dir = os.path.dirname(os.path.abspath(__file__))


def run_gcloud_command(command: str, state: Annotated[dict, InjectedState]) -> str:
    """
    Execute a gcloud command.
    gcloud: Command-line interface for Google Cloud Platform, used to manage cloud resources, 
    deploy services, configure infrastructure, and interact with GCP APIs.

    Args:
        command (str): The gcloud command to execute (e.g., "gcloud compute instances list")
        state: Automatically injected by the system - do not include this parameter in tool calls.
        
    Returns:
        str: The stdout output from the gcloud command if successful, or an error message
             if the command fails or encounters an exception.
             
    Raises:
        FileNotFoundError: If the service account key file is not found
        json.JSONDecodeError: If the service account key file is malformed
        subprocess.CalledProcessError: If the gcloud command fails to execute
    """
    try:
        if command.split(' ')[0] != 'gcloud':
            return f"Error: gcloud command not found in the command: {command}"
            
        sa_key_path = os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"], "sa_key.json"))
        
        # Get project id from sa_key.json
        with open(sa_key_path, "r") as f:
            sa_key = json.load(f)
        project_id = sa_key["project_id"]
        
        # Set environment variables
        env = os.environ.copy()
        env["GOOGLE_APPLICATION_CREDENTIALS"] = sa_key_path
        
        # First, authenticate gcloud with the service account
        auth_cmd = f"gcloud auth activate-service-account --key-file={sa_key_path}"
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True, env=env)
        
        if auth_result.returncode != 0:
            return f"Error authenticating with service account: {auth_result.stderr}"
        
        # Set the project
        project_cmd = f"gcloud config set project {project_id}"
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True, env=env)
        
        if project_result.returncode != 0:
            return f"Error setting project: {project_result.stderr}"
        
        # Run the actual command
        cmd = f"{command} --project={project_id}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
        return result
    except Exception as e:
        return f"Error running gcloud command: {e}"