import os
import ast
import subprocess
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))

def edit(file_path: str, new_code: str, starting_line: int, ending_line: int, state: Annotated[dict, InjectedState]):
    """
    This tool replaces the contents of a file from starting_line to ending_line (inclusive) with the provided new_code string. Useful for patching or updating code snippets in-place.

    Args:
        file_path (str): Path to the file (relative to codebase root, e.g., 'repo/main.py').
        new_code (str): The code to insert in place of the specified lines.
        starting_line (int): The first line to replace (1-based, inclusive).
        ending_line (int): The last line to replace (1-based, inclusive).
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        str: Success message if the edit is applied, or an error message if starting_line < 1 or another error occurs.

    Example:
        >>> edit(
        ...     file_path='repo/main.py',
        ...     new_code='print("Patched!")',
        ...     starting_line=5,
        ...     ending_line=7
        ... )

    Edge Cases:
        - If starting_line < 1, returns an error.
        - If ending_line exceeds file length, only available lines are replaced.
        - If the file does not exist, raises an exception.
        - If there's syntax errors, raise an exception
    """
    starting_line = int(starting_line)
    ending_line = int(ending_line)

    full_path = os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"], "codebase", file_path))
    session_dir = os.path.dirname(full_path)

    if not os.path.exists(full_path):
        return f"Error: File '{file_path}' does not exist."

    if starting_line < 1:
        return "Error: Starting line must be greater than 0."

    with open(full_path, "r") as file:
        lines = file.readlines()

    # Patch the lines
    updated_lines = lines[:]
    updated_lines[starting_line - 1:ending_line] = [new_code if new_code.endswith("\n") else new_code + "\n"]

    updated_code = "".join(updated_lines)

    with open(full_path, "w") as file:
        file.writelines(updated_lines)

    return "File edited successfully"
