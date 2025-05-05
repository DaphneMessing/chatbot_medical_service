# logic/azure_calls.py

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from typing import List, Optional

# Load environment variables
load_dotenv()
CHAT_KEY = os.getenv("AZURE_OPENAI_KEY")
CHAT_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")  
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBD_DEPLOYMENT")   

client = AzureOpenAI(
    api_key=CHAT_KEY,
    azure_endpoint=CHAT_ENDPOINT,
    api_version="2025-01-01-preview"
)
 

def get_chat_completion(messages: List[dict], temperature: float = 0.4, tools: Optional[List[dict]] = None, tool_choice: Optional[str] = None, return_raw: bool = False) -> str:
    """Get a GPT chat completion, with optional tool calling."""
    response = client.chat.completions.create(
        model=CHAT_DEPLOYMENT, 
        messages=messages,
        temperature=temperature,
        tools=tools,
        tool_choice=tool_choice
    )
    if return_raw:
        return response
    return response.choices[0].message.content.strip()

def get_embedding(text: str) -> List[float]:
    """Generate ADA-002 embedding for the given text."""
    response = client.embeddings.create(
        input=[text],
        model=EMBEDDING_DEPLOYMENT
    )
    return response.data[0].embedding
