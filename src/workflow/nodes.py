import sys
from tools.edit_tool import edit
from tools.pr_tool import create_pull_request
from tools.view_tool import view
from tools.search_tool import search
from tools.gcloud_command_tool import run_gcloud_command
from tools.terraform_tool import terraform_command_executor
from tools.create_file_tool import create_file
from tools.list_directory_contents_tool import list_directory_contents
from tools.clone_repository_tool import clone_repository
from tools.retrieve_log_tool import retrieve_logs
from utlis.gcp.get_sakey import download_save_sakey
import re
from llm_factory.google import GoogleGen
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,ToolMessage,RemoveMessage
import time
import subprocess
import os
from pathlib import Path
import shutil
import json
import  logging
from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))

def load_prompt(template_name, **kwargs):
    env = Environment(loader=FileSystemLoader(os.path.join(current_dir, '..', 'prompts', 'templates')))
    template = env.get_template(template_name)
    return template.render(**kwargs)


class Nodes():
    def __init__(self):
        self.llm_obj=GoogleGen()
        self.tools=[edit,
        create_pull_request,
        view,
        search,
        terraform_command_executor,
        create_file,
        list_directory_contents,
        clone_repository,
        retrieve_logs,
        run_gcloud_command]
        self.tool_names=[func.__name__ for func in self.tools]
        self.llm_obj.llm_with_tools=self.llm_obj.llm.bind_tools(self.tools)
    def initiate_state(self,state):
        logger.info('entering initial state')
        ## save sa_key
        download_save_sakey(state["sa_key_bucket_link"],session_id=state["session_id"])
        return {}
    def router(self, state):
        """
        LLM-based router node that decides whether to send the query to the planner or to a simple chatbot.
        """
        logger.info('entering router node')
        # You can use a simple prompt to classify the query
        # Load the system prompt template

        system_prompt= load_prompt("router_prompt.jinja")
        messages = [SystemMessage(content=system_prompt),
                    HumanMessage(content=f"User Query: {state['query']}\n")]
        response = self.llm_obj.llm.invoke(messages)
        decision = response.content.strip().lower()
        logger.info(f"Router decision: {decision}")
        if decision == "code":
            return "planner"
        else:
            return "chatbot"

    def chatbot(self, state):
        """
        Simple chatbot node for general conversation.
        """
        logger.info('entering chatbot node')
        system_prompt= load_prompt("chatbot_prompt.jinja")
        messages = [SystemMessage(content=system_prompt),
                    HumanMessage(content=f"User Query: {state['query']}\n")]
        response = self.llm_obj.llm.invoke(messages)
        return {"agent_response": response.content,
                "input_tokens":response.usage_metadata["input_tokens"]+state.get('input_tokens',0),
                "output_tokens":response.usage_metadata["output_tokens"]+state.get('output_tokens',0)}
    def preplanner(self,state):
        trajectory = ["Executor Actions: \n"]
        for msg in state['executor_messages']:
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
                entry = f"TOOL RESPONSE: {msg.content}"
                tool_call_id = getattr(msg, 'tool_call_id', None)
                if tool_call_id:
                    entry += f"\n  Tool Call ID: {tool_call_id}"
                trajectory.append(entry)
        return {"previous_steps_actions":state["previous_steps_actions"]+["\n---\n".join(trajectory)]}
    def planner(self, state):
        """
        Planner node that analyzes the query and creates a plan for execution.
        Uses the LLM to generate a step-by-step plan based on the user query.
        """
        logger.info('entering planner state')
        ### PLANNER
        # Load the system prompt template
        system_prompt= load_prompt("planner_prompt.jinja",
            codebase=state['codebase'],
            previous_steps_actions="\n".join(state.get('previous_steps_actions',[" "])),
            tool_names=self.tool_names)
        # Create messages for the planner
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Query: {state['query']}\n")
        ]
        
        # Get response from LLM
        response = self.llm_obj.llm.invoke(messages)
        logger.info(f"CURRENT TASK\n {response.content}\n\n")

        ### EXECUTOR
        # Load the system prompt template
        system_prompt= load_prompt("executor_prompt.jinja",
            codebase=state['codebase'],
            tool_names=self.tool_names,
            previous_steps_actions="\n".join(state.get('previous_steps_actions',[" "])),
            current_step=response.content)
        # logger.info(f"Executor SYSTEM PROMPT\n {system_prompt}\n\n")
        executor_messages= [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Query: {state['query']}\n")
        ]
        clear_messages = [RemoveMessage(id=msg.id) for msg in state['executor_messages']]
        
        return {"executor_messages": clear_messages + executor_messages,
                "previous_steps_actions":state.get('previous_steps_actions',[])+[f"STEP: \n{response.content}"],
                "current_step":response.content,
                "plans":state.get('plans',[])+[response.content],
                "current_cycle":0,
                "input_tokens":response.usage_metadata["input_tokens"]+state.get('input_tokens',0),
                "output_tokens":response.usage_metadata["output_tokens"]+state.get('output_tokens',0)}
    
    def executor(self, state):
        """
        Executor node that takes the plan and executes the necessary tools.
        Uses the LLM with tools to execute the planned actions.
        """
        logger.info('entering executor state')
        logger.info(f'{len(state["executor_messages"])}')
        logger.info(f'{len(state["messages_for_evaluation"])}')
        logger.info("------------------------------------------")
        logger.info(f"INPUT_TOKENS:-------->{state.get('input_tokens',0)}")
        logger.info(f"OUTPUT_TOKENS:------->{state.get('output_tokens',0)}")
        if isinstance(state['executor_messages'][-1], ToolMessage):
            logger.info(f"TOOL RESPONSE: {state['executor_messages'][-1].content}")
        if state["current_cycle"]<state["max_cycle_executor"]:
            response=[self.llm_obj.llm_with_tools.invoke(state['executor_messages'])]
        else:
            response=[AIMessage(content="Alright, What do you think?")]
            return {"executor_messages":response,"messages_for_evaluation":response,"current_cycle":state['current_cycle']+1}
        logger.info(f'executor agent thought: {response[0].content}\n')
        logger.info(f'executor agent call tools: {response[0].additional_kwargs}\n\n') 
        if len(state['executor_messages'])>2 and state['executor_messages'][-2].additional_kwargs==response[0].additional_kwargs:
            logger.info(f'Same call tool!')
            response=[AIMessage(content="Alright, What do you think?")]
            return {"executor_messages":response,"messages_for_evaluation":response,"current_cycle":state['current_cycle']+1}
        logger.info('Agent sleeping')
        time.sleep(10)
        logger.info('Wake up')
        return {"executor_messages":response,
                "messages_for_evaluation":response,
                "current_cycle":state['current_cycle']+1,
                "input_tokens":response[0].usage_metadata["input_tokens"]+state.get('input_tokens',0),
                "output_tokens":response[0].usage_metadata["output_tokens"]+state.get('output_tokens',0)}
    
    

    def planner_decision(self, state):
        """
        Decision function for the planner node.
        Determines whether to continue to executor or end the workflow.
        Checks if the current step indicates that the task is already completed or cannot be completed.
        """
        logger.info('making planner decision')

        current_step = state.get('current_step', '').strip().lower()

        # Check for structured completion response
        pattern = r"^reasoning:\s*(.+?)\s*step:\s*done$"
        if re.match(pattern, current_step, re.IGNORECASE | re.DOTALL):
            return '__end__'

        return "executor"
    def summarizer(self, state):
        """
        Summarizer node that provides a user-friendly summary of what the planner did.
        """
        logger.info('entering summarizer node')
        system_prompt= load_prompt("summarizer_prompt.jinja",user_query=state['query'])
        messages = [SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Planner Actions and Decisions:\n{state.get('previous_steps_actions', '')}\n")] 
        response = self.llm_obj.llm.invoke(messages)
        return {"agent_response": response.content,
                "input_tokens":response.usage_metadata["input_tokens"]+state.get('input_tokens',0),
                "output_tokens":response.usage_metadata["output_tokens"]+state.get('output_tokens',0)}
    
    def final_state(self,state):
        # USED to clean cache if ANY
        logger.info('entering final state')
        # Upload the current session box into bucket
        return {}