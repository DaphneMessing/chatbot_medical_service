# tools.py
from typing import Literal
import json
import logging
from typing import List
import logging

# USER INFORMATION COLLECTION
def collect_name(first_name: str, last_name: str) -> str:
    # Check if both first and last names are provided and not empty
    if first_name.strip() and last_name.strip():
        return json.dumps({
        "message": f"Great, {first_name} {last_name}! Could you please provide your 9-digit ID number?"
    })
    return "Please provide both first and last name."

def collect_id_number(id_number: str) -> str:
    # Check if the ID number is exactly 9 digits long and consists of digits only
    if len(id_number) == 9 and id_number.isdigit():
        return json.dumps({
        "message": "Thank you. Now, please tell me your gender (e.g., Male, Female, Other)."
    })
    return "ID must be exactly 9 digits."

def collect_gender(gender:str) -> str:
    # Check if the gender is one of the specified options
    if gender.lower() in ["male", "female", "other"]:
        return json.dumps({
        "message": "Got it. Could you please provide your age?"
    })
    return "Gender must be 'Male', 'Female' or 'Other'."

def collect_age(age: int)  -> str:
    # Check if the age is a number between 0 and 120
    if 0 <= age <= 120 and isinstance(age, int):
        return json.dumps({
        "message": "Thanks! Could you please provide your HMO? (e.g., Maccabi, Clalit, Meuhedet)"
    })
    return "Age must be a number between 0 and 120."

def collect_hmo(hmo: str) -> str:
    if hmo.lower() in ["maccabi", "meuhedet", "clalit"]:
        return json.dumps({
            "message":f"Great. Could you provide your 9-digit HMO card number?",
            "hmo": hmo.lower()
        })
    return "HMO must be one of: Maccabi, Meuhedet, Clalit."

def collect_card_number(card_number: str) -> str:
    # Check if the card number is exactly 9 digits long and consists of digits only
    if len(card_number) == 9 and card_number.isdigit():
        return json.dumps({
            "message": "Great. Lastly, what is your insurance membership tier? (זהב / כסף / ארד)",
            "card_number": card_number
        })
    return json.dumps({
        "message": "Thanks. Lastly, what is your insurance membership tier? (זהב / כסף / ארד)"
    })

def collect_insurance_tier(tier: str) -> str:
    # Check if the insurance tier is one of the specified options
    if tier in ["Gold", "Silver", "Bronze"]:
        return json.dumps({
        "message": "Thanks! Please confirm that all your information is correct by replying 'yes' or 'no'.",
        "tier": tier.lower()
        })
    return "Insurance Tier must be one of: Gold, Silver, Bronze."


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

# --- Tool Descriptions for OpenAI Function Calling ---

tool_descriptions = [
        {
        "type": "function",
        "function": {
            "name": "collect_name",
            "description": "Collects the user's first and last name. First name should be a string and last name should be a string. Be sure to ask for both names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"}
                },
                "required": ["first_name", "last_name"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_id_number",
            "description": "Collects a valid Israeli 9-digit ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_number": {"type": "string"}
                },
                "required": ["id_number"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_gender",
            "description": "Collects the user's gender.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender": {"type": "string", "enum": ["Male", "Female", "Other"]}
                },
                "required": ["gender"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_age",
            "description": "Collects the user's age (0-120).",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer"}
                },
                "required": ["age"]
            },
        },
    },
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
            "name": "collect_card_number",
            "description": "Collects the user's 9-digit HMO card number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_number": {"type": "string"}
                },
                "required": ["card_number"]
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
