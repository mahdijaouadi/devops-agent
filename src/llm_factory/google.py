from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from llm_factory.llm_config import LLM_CONFIG
import os


class GoogleGen():
    def __init__(self):
        load_dotenv()
        config = LLM_CONFIG["gemini"]
        api_key = os.getenv(config["api_key_env"])
        self.llm = ChatGoogleGenerativeAI(model=config["model_name"], temperature=0, google_api_key=api_key)    
    def __call__(self, messages):
        response=self.llm.invoke(messages)
        return response