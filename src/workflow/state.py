from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    query: str
    codebase: list
    session_repositories: list
    session_id: str
    githubapp_id: str
    githubapp_privatekey: str
    sa_key_bucket_link: dict
    current_step: str
    plans: list
    previous_steps_actions: list
    current_cycle: int
    max_cycle_executor: int
    agent_response: str
    input_tokens: int
    output_tokens: int
    executor_messages: Annotated[list,add_messages]
    messages_for_evaluation: Annotated[list,add_messages]