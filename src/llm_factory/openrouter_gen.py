from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

class OpenrouterGen():
    def __init__(self):
        load_dotenv() 
        llm = ChatOpenAI(
            model="openai/chatgpt-4o-latest",
            temperature=0,
            base_url="https://openrouter.ai/api/v1"
        )
    def __call__(self, messages):
        response=self.llm.invoke(messages)
        return response
    