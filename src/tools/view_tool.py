import os
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
current_dir = os.path.dirname(os.path.abspath(__file__))

def view(file_path: str, starting_line: int, ending_line:int,state: Annotated[dict, InjectedState]):
    """
    This tool reads a file and returns a window of lines, including context about lines above and below the window. Useful for previewing code or text files without loading the entire file.

    Args:
        file_path (str): Path to the file (relative to codebase root, e.g., 'repo/main.py').
        starting_line (int): The first line to include (1-based, inclusive).
        ending_line (int): The last line to include (1-based, inclusive).
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        str: The requested lines, with line numbers, and notes about lines above and below. If the starting line is less than 1, returns an error message.

    Example:
        >>> view(
        ...     file_path='repo/main.py',
        ...     starting_line=10,
        ...     ending_line=20
        ... )

    Edge Cases:
        - If starting_line < 1, returns an error.
        - If ending_line exceeds file length, returns available lines and notes the number of lines below is zero.
        - If the file does not exist, raises an exception.
    """
    starting_line = int(starting_line)
    ending_line = int(ending_line)

    with open(os.path.abspath(os.path.join(current_dir, "..", "tmp",state["session_id"], "codebase", file_path)), "r") as file:
        lines = file.readlines()
    if starting_line>0:
        window=lines[starting_line-1:ending_line]
        number_lines_above=starting_line-1
        number_lines_below=len(lines)-ending_line
        if number_lines_below <=0:
            number_lines_below=0
        for i in range(len(window)):
            window[i]=f"{i+1}: {window[i]}"
        window.insert(0,f"There's {number_lines_above} lines above\n")
        window.append(f"\nThere's {number_lines_below} lines below\n")
        return "".join(window)
    else:
        return "Starting line must be greater than 0"