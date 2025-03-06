import os
from dotenv import load_dotenv
import json

load_dotenv()  # Carrega variáveis do .env

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")

PIPER_MODELS = {
    "en": "/home/matheus/projetos/piper/models/en_US-ryan-high.onnx",
    "pt": "/home/matheus/projetos/piper/models/pt_BR-faber-medium.onnx",
    "es": "/home/matheus/projetos/piper/models/es_MX-claude-high.onnx",
    "zh": "/home/matheus/projetos/piper/models/zh_CN-huayan-medium.onnx",
    "default": "/home/matheus/projetos/piper/models/pt_BR-faber-medium.onnx"
}

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_on_web",
        "description": "Gather context when explicitly resquested by the user from the internet",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                  "type": "string",
                    "description": "The search for the subject that user explicitly resquested you to look for"
                }
            },
            "required": ["query"]
        }
    }
}

SYSTEM_INSTRUCTION = f"""
Today's Date: March 6, 2025.
language: Always reply in the language used by the user to maintain consistency in communication.

Behavior:

You are a friendly person with access to web searches for up-to-date information.
Use provided research context when available.
Maintain a conversational, natural, and engaging tone.
Avoid robotic or overly structured responses—respond as naturally as possible.
Keep responses concise and relevant.
"""
# Only search the web when the user explicitly requests it. example "Search for this subject, bring me the lasts/recently news, etc..."

# Web Search Rules:
# Perform a search when:
# Fact-checking or statistical verification is needed.
# The user requests news or current events.

# Response Guidelines:
# Prioritize the "answer" in the search results.
# Use "sources" only for additional details.

# Available Tool: {json.dumps(TOOL_SCHEMA)}

