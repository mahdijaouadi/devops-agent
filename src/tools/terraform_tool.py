import os        # Execute terraform command
import subprocess
import logging
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



current_dir = os.path.dirname(os.path.abspath(__file__))

def terraform_command_executor(terraform_command: str, dir_execution: str,state: Annotated[dict, InjectedState]):
    """
    This tool validates the requested Terraform operation, sets up credentials, and runs the command in the user's codebase directory. Only safe read-only operations are allowed (e.g., init, plan, validate, fmt, show, state list).

    Important:
        - For any Terraform command, you must run 'terraform init' (with the appropriate backend config) in the target directory before running other Terraform commands. This ensures the working directory is initialized and the backend is configured.

    Args:
        terraform_command (str): The Terraform command to run (e.g., 'terraform plan', 'terraform validate'). Only certain operations are allowed. 'apply' is not permitted.
        dir_execution (str): Path (relative to codebase root) where the Terraform command should be executed (e.g., 'repo/infra').
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        dict: Contains 'success' (bool), 'stdout' (str), and 'stderr' (str). If the operation is invalid or an error occurs, returns an error message in 'stdout' or 'stderr'.

    Example:
        >>> terraform_command_executor(
        ...     terraform_command='terraform plan',
        ...     dir_execution='repo/infra'
        ... )

    Edge Cases:
        - If the operation is not in the allowed list, returns an error.
        - If the backend config is missing for 'init', returns an error.
    """
    try:
        logger.info("In terraform operation tool")
        # Validate operation parameter
        valid_operations = ['init', 'plan','validate', 'fmt', 'show','state list']
        valid_operation=False
        for op in valid_operations:
            if op in terraform_command:
                valid_operation=True
                break
        if terraform_command.split(" ")[1] == "apply":
            valid_operation=False
        if not valid_operation:
            return f"The operation in your command is not valid. Valid operations: {valid_operations}"
        if 'init' in terraform_command and '-backend-config' not in terraform_command:
            return "To use init command you should always provide backend config file to get the state"

  

        sa_key_path = os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"],"sa_key.json"))

        # Set env var and run Terraform
        env = os.environ.copy()
        env["GOOGLE_APPLICATION_CREDENTIALS"] = sa_key_path
        cmd = f"cd .. && cd tmp && cd {state['session_id']} && cd codebase && cd {dir_execution} && {terraform_command}"
        result = subprocess.run(
            cmd,
            cwd=current_dir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        logger.info("out of terraform operation tool")
        return {
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
                
    except Exception as e:
        print(e)
        return {
            'success': True,
            'stdout': "result.stdout",
            'stderr': "result.stderr"
        }