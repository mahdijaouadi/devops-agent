from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))

def create_file(file_path: str, content: str,state: Annotated[dict, InjectedState]):
    """
    This tool creates a file at the given path, ensuring it is placed inside one of the allowed repositories in the codebase. It checks for directory traversal and codebase root violations.

    Args:
        file_path (str): Path to the new file (relative to codebase root, e.g., 'repo/newfile.py'). Must be inside a valid repository folder.
        content (str): Content to write to the new file.
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        dict: {'success': str} if the file is created, or {'error': str} with a message if creation fails or is not allowed.

    Example:
        >>> create_file(
        ...     file_path='repo/newfile.py',
        ...     content='print("Hello, world!")'
        ... )

    Edge Cases:
        - If the file path is not inside a valid repo, returns an error.
        - If the file already exists, it will be overwritten.
    """
    try:
        codebase_dir = os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"], "codebase"))
        codebase = os.listdir(codebase_dir)
        first_folder=file_path.split("/")[0]
        if first_folder not in codebase:
            return {"error": f"The file is not created because you should place the file inside one of the provided repositories in the codebase. {codebase}"}
        # Resolve absolute path
        abs_path = os.path.abspath(os.path.join(codebase_dir, file_path))

        # Ensure the file path is within the codebase directory
        if not abs_path.startswith(codebase_dir):
            return {"error": f"File path is outside the codebase directory. You should place the file inside one of the provided repositories in the codebase. {codebase}"}

        # Check if the file is directly inside the codebase root (i.e., not inside a subfolder/repo)
        relative_path = os.path.relpath(abs_path, codebase_dir)
        if len(relative_path.split(os.sep)) == 1:
            return {"error": f"The file is not created because you should place the file inside one of the provided repositories in the codebase. {codebase}"}

        # Create directories if necessary
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # Write the file
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"success": f"File created at {abs_path}"}
    except Exception as e:
        return {"error": str(e)}
