import subprocess
import os
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
current_dir = os.path.dirname(os.path.abspath(__file__))
def run_command(command, cwd):
    return subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def list_directory_contents(dir_path, state: Annotated[dict, InjectedState]):
    """
    This tool returns the names of files and subdirectories in the specified directory. For files, it also reports the number of lines. Useful for codebase exploration and navigation.

    Args:
        dir_path (str): Path to the directory (relative to codebase root, e.g., 'repo/').
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        dict: {'items': list of str} with file/subdirectory names and line counts, or {'error': str} if the directory is not found or another error occurs.

    Example:
        >>> list_directory_contents(dir_path='repo/')

    Edge Cases:
        - If the directory does not exist, returns an error.
        - If a file cannot be read, it is skipped or an error is returned.
    """
    try:
        abs_dir_path = os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"], "codebase", dir_path))
        if not os.path.isdir(abs_dir_path):
            return {"error": f"Directory '{dir_path}' not found."}
        
        items = []
        for item in os.listdir(abs_dir_path):
            item_path = os.path.join(abs_dir_path, item)
            if os.path.isfile(item_path):
                try:
                    with open(item_path, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                    items.append(f"{item}, it has {line_count} lines")
                except:
                    continue
            else:
                items.append(item)

        return {
            "items": items
        }
        
    except FileNotFoundError:
        return {"error": f"Directory '{dir_path}' not found."}
    except Exception as e:
        return {"error": str(e)}
