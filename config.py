import os
from dotenv import load_dotenv
import json
import time

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
  "name": "search_on_web",
  "description": "Search tool. Use to get real-time information",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "A focused keyword or phrase representing what you are searching for."
      },
      "search_type": {
        "type": "string",
        "enum": ["news", "finance", "general"],
        "description": "Determines the category of search results to return, with options including news articles ('news'), financial data ('finance'), or a general web-wide query ('general'). The default setting is 'general'.",
        "default": "general"
      },
      "time_range": {
        "type": "string",
        "enum": ["none", "day", "week", "month", "year"],
        "description": "Limits the search results to occur within certain time frames, with options such as no limit ('none'), a single day ('day'), up to one week ('week'), an entire month ('month'), or all year round ('year'). The default setting is 'none'.",
        "default": "none"
      }
    },
    "required": ["query"]
  }
}

SYSTEM_INSTRUCTION = f"""
Current date and time:
- {time.ctime()}

Tone of conversation:
- You are an empathetic and curious assistant with some tools.

Response rules:
- Say something and then ask the user a question.
- Respond in the user's language.

Research rules:
RP 1: When the user asks something about you, respond directly.
RP 2: If the user asks or inquires about anything, you should search the internet using the tool {json.dumps(TOOL_SCHEMA)}.
"""
# if you are authorized search on web, call the tool before the reply.
# Available Tool: {json.dumps(TOOL_SCHEMA)}
# SYSTEM_INSTRUCTION = f"""
# Today's Date: March 6, 2025.
# language: Always reply in the language used by the user to maintain consistency in communication.

# Behavior:

# You are a friendly person with access to web searches for up-to-date information.
# Use provided research context when available.
# Maintain a conversational, natural, and engaging tone.
# Avoid robotic or overly structured responses—respond as naturally as possible.
# Keep responses concise and relevant.
# """
# Only search the web when the user explicitly requests it. example "Search for this subject, bring me the lasts/recently news, etc..."

# Web Search Rules:
# Perform a search when:
# Fact-checking or statistical verification is needed.
# The user requests news or current events.

# Response Guidelines:
# Prioritize the "answer" in the search results.
# Use "sources" only for additional details.

# Available Tool: {json.dumps(TOOL_SCHEMA)}

