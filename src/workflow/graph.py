import sys
from workflow.nodes import Nodes
from workflow.state import State
import requests
from typing import Any
import json
from typing_extensions import Annotated
from langgraph.graph import START,END,StateGraph
from langgraph.prebuilt import ToolNode,tools_condition
from langgraph.checkpoint.memory import MemorySaver
import os
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

current_dir = os.path.dirname(os.path.abspath(__file__))


def custom_tool_node(state):
    """
    Custom tool node that executes tools and returns responses in executor_messages field
    instead of messages field.
    """
    # Get the last message which should be an AIMessage with tool calls
    last_message = state['executor_messages'][-1]
    
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {}
    
    # Execute each tool call
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        
        # Find the tool function
        tool_func = None
        for tool in Nodes().tools:
            if tool.__name__ == tool_name:
                tool_func = tool
                break
        
        if tool_func:
            try:
                # Filter out 'state' from tool_args since it's injected automatically
                filtered_args = {k: v for k, v in tool_args.items() if k != 'state'}
                # Execute the tool with the state
                result = tool_func(**filtered_args, state=state)
                # Create a ToolMessage
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call['id']
                )
                tool_messages.append(tool_message)
            except Exception as e:
                # Create an error ToolMessage
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call['id']
                )
                tool_messages.append(error_message)
    
    # Return the tool messages in executor_messages field
    return {"executor_messages": tool_messages,'messages_for_evaluation':tool_messages}

def tools_condition_executor(state):
    messages = state.get("executor_messages", [])
    if not messages:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"

class WorkFlow():
    def __init__(self,request):
        nodes=Nodes()
        self.workflow=StateGraph(State)
        #NODES
        self.workflow.add_node('initiate_state',nodes.initiate_state)
        self.workflow.add_node('chatbot',nodes.chatbot)
        self.workflow.add_node('preplanner',nodes.preplanner)
        self.workflow.add_node('planner',nodes.planner)
        self.workflow.add_node('executor',nodes.executor)
        self.workflow.add_node('tools',custom_tool_node)
        self.workflow.add_node('summarizer',nodes.summarizer)
        self.workflow.add_node('final_state',nodes.final_state)

        #EDGES
        self.workflow.add_edge(START,'initiate_state')
        self.workflow.add_conditional_edges('initiate_state',nodes.router,{'planner':'planner','chatbot':"chatbot"})

        self.workflow.add_edge('chatbot','final_state')
        self.workflow.add_conditional_edges('planner',nodes.planner_decision,{'executor':'executor','__end__':"summarizer"})
        self.workflow.add_conditional_edges('executor',tools_condition_executor,{'tools':'tools','__end__':"preplanner"})
        self.workflow.add_edge('tools','executor')
        self.workflow.add_edge('preplanner','planner')
        self.workflow.add_edge('summarizer','final_state')

        memory=MemorySaver()
        self.workflow = self.workflow.compile(checkpointer=memory)
        self.config={'configurable':{'thread_id':request.session_id},"recursion_limit": 25}
    def __call__(self,request):
        response=self.workflow.invoke({"query":request.query,
                                       "codebase":request.codebase,
                                       "session_id":request.session_id,
                                       "githubapp_id":os.environ.get("GITHUBAPP_ID"),
                                       "githubapp_privatekey":os.environ.get("GITHUBAPP_PRIVATE_KEY"),
                                       "sa_key_bucket_link":request.sa_key_bucket_link,
                                       "max_cycle_executor":2,
                                       },self.config)
        return response
    def start_specific_node(self,state,starting_node):        
        self.workflow.set_entry_point(starting_node)
        response=self.workflow.invoke(state)
        return response
    def show_state(self):
        for m in self.workflow.get_state(self.config).values['messages_for_evaluation']:
            m.pretty_print()
    def return_state_value(self,state_name):
        state_value_list=[]
        for m in self.workflow.get_state(self.config).values[state_name]:
            state_value_list.append(m)
        return state_value_list

    def messages_to_trajectory_string(self):
        """
        Convert a list of messages into a string trajectory, ignoring HumanMessage and SystemMessage.
        For AIMessage, include content and tool calls. For ToolMessage, include content and tool_call_id.
        """
        trajectory = []
        for msg in self.workflow.get_state(self.config).values['messages_for_evaluation']:
            if isinstance(msg, (HumanMessage, SystemMessage)):
                continue
            elif isinstance(msg, AIMessage):
                entry = f"AI: {msg.content}"
                # Tool calls (if any)
                tool_calls = getattr(msg, 'tool_calls', None)
                if tool_calls:
                    entry += f"\n  Tool Calls: {tool_calls}"
                trajectory.append(entry)
            elif isinstance(msg, ToolMessage):
                entry = f"TOOL: {msg.content}"
                tool_call_id = getattr(msg, 'tool_call_id', None)
                if tool_call_id:
                    entry += f"\n  Tool Call ID: {tool_call_id}"
                trajectory.append(entry)
            else:
                # Fallback for unknown message types
                entry = f"{type(msg).__name__}: {getattr(msg, 'content', str(msg))}"
                trajectory.append(entry)
        return "\n---\n".join(trajectory)