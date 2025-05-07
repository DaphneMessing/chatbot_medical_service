
from typing import Literal
import json
import logging
from typing import List
import logging




def collect_hmo(hmo: str) -> str:
    if hmo.lower() in ["maccabi", "meuhedet", "clalit"]:
        return json.dumps({
            "message": f"Great. What is your insurance membership tier? (זהב / כסף / ארד)",
            "hmo": hmo.lower()
        })
    return "HMO must be one of: Maccabi, Meuhedet, Clalit."

def collect_insurance_tier(tier: str) -> str:
    # Check if the insurance tier is one of the specified options
    if tier in ["Gold", "Silver", "Bronze"]:
        return json.dumps({
        "message": "Thanks! Please confirm that all your information is correct by replying 'yes' or 'no'.",
        "tier": tier.lower()
        })
    return "Insurance Tier must be one of: Gold, Silver, Bronze."

# def confirm_information(confirmation: str) -> str:
#     if confirmation.lower() == "yes":
#         return json.dumps({
#             "message": "✅ Thanks for confirming! You may now ask me questions about your health services.",
#             "confirmed": True
#         })
#     else:
#         return json.dumps({
#             "message": "Okay. Please restart the form and provide your information again.",
#         })

def confirm_information(confirmation: str) -> str:
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 confirm_information received: {confirmation}")
    if confirmation.lower() in ["yes"]:
        return json.dumps({
            "message": f"✅ Thanks for confirming! You may now ask me questions about your health services",
            "confirmed": True
        })
    elif confirmation.lower() in ["no"]:
        return json.dumps({
            "message": f"Okay. Please restart the form and provide your information again.",
            "confirmed": False
        })
    else:
        return json.dumps({
            "message": f"Invalid response. Please reply with 'yes' or 'no'.",
            "confirmed": False
        })







    # if "yes" in confirmation.lower():
    #     return json.dumps({
    #         "message": "✅ Thanks for confirming! You may now ask me questions about your health services.",
    #         "confirmed": True
    #     })
    # else:
    #     return json.dumps({
    #         "message": "Okay. Please restart the form and provide your information again.",
    #         "confirmed": False
    #     })
    




# --- Tool Descriptions for OpenAI Function Calling ---

tool_descriptions = [
    {
        "type": "function",
        "function": {
            "name": "collect_hmo",
            "description": "Collects the user's HMO (Maccabi, Meuhedet, Clalit).",
            "parameters": {
                "type": "object",
                "properties": {
                    "hmo": {"type": "string", "enum": ["Maccabi", "Meuhedet", "Clalit"]}
                },
                "required": ["hmo"]
            },
        },
    },
    
    {
        "type": "function",
        "function": {
            "name": "collect_insurance_tier",
            "description": "Collects the user's insurance tier (Gold, Silver, Bronze).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tier": {"type": "string", "enum": ["Gold", "Silver", "Bronze"]}
                },
                "required": ["tier"]
            },
        },
    },

        {
        "type": "function",
        "function": {
            "name": "confirm_information",
            "description": "Confirm user information has been collected correctly.",
            "parameters": {
                "type": "object",
                "properties": {"confirmation": {"type": "string", "enum": ["yes", "no"]}},
                "required": ["confirmation"],
            },
        },
    },

]
