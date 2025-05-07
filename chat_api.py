
# main.py

import os
import logging
import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from logic.azure_calls import get_chat_completion, get_embedding
from tools import tool_descriptions, collect_hmo, collect_insurance_tier, confirm_information
from src.extract_data_embd import run_extraction
from src.embd_chunks import normalize_hmo_tier, load_data, get_top_matches, get_answer_from_metadata, filter_by_hmo_tier, build_and_save_index, is_kb_ready
from pathlib import Path
from typing import List, Optional, Dict, Any



# Set up logging
os.makedirs("logs", exist_ok=True)
log_file = "logs/chatbot.log"
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger = logging.getLogger()  # Root logger
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)
logger.info("🚀 FastAPI server started and logging is working.")


app = FastAPI()

if not is_kb_ready():
    print("\n🔧 Knowledge base not found. Building it...")
    run_extraction()
    build_and_save_index()
    print("✅ Knowledge base built.")
else:
    print("✅ Knowledge base is already ready. Skipping build.")


def load_system_prompt(language: str) -> str:
    prompt_dir = Path(__file__).resolve().parent / "prompts"
    filename = "info_prompt_en.txt" if language == "english" else "info_prompt_he.txt"
    with open(prompt_dir / filename, "r", encoding="utf-8") as f:
        return f.read()

def handle_tool_call(tool_name: str, arguments: str):
    data = json.loads(arguments)
    if tool_name == "collect_hmo":
        return collect_hmo(data["hmo"])
    elif tool_name == "collect_insurance_tier":
        return collect_insurance_tier(data["tier"])
    elif tool_name == "confirm_information":
        return confirm_information(data["confirmation"])
    return "Unknown tool call."    



def translate_to_hebrew(text: str) -> str:
    system_message = """
    You are a helpful assistant that translates English to Hebrew. 
    You will be given a question in English related to medical services in Israel.
    Your task is to translate it to Hebrew.
    Translate the following question from English to Hebrew. Respond with Hebrew only.\n
    If the following words are in the text, use this mapping to transtlate them: 
    'HMO' -> 'קופת חולים', 'insurance tier' -> 'רמת ביטוח', 'medical services' -> 'שירותי בריאות', 'maccabi' -> 'מכבי', 'clalit' -> 'כללית', 'meuhedet' -> 'מאוחדת'.
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": text}
    ]
    response = get_chat_completion(messages)
    return response.strip()


# Enable CORS (for Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use exact origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request body
class ChatRequest(BaseModel):
    history: list
    user_input: str
    language: str 
    hmo: str = ""
    tier: str = ""
    confirmed: str= ""


class Phase2Request(BaseModel):
    hmo: str
    tier: str
    lang: str
    question: str

@app.post("/phase_1")
async def phase_1(request: ChatRequest):
    print("✅ /phase_1 endpoint was called")
    try:
        logger.info("📥 Received request:")
        logger.info(f"Language: {request.language}")
        logger.info(f"HMO: {request.hmo}, Tier: {request.tier}, Confirmed: {request.confirmed}")
        logger.info(f"User Input: {request.user_input}")
        logger.info(f"History Length: {len(request.history)}")

        system_prompt = load_system_prompt(language=request.language)
        logger.info("📄 Loaded system prompt")

        messages = [{"role": "system", "content": system_prompt}]
        if not request.history and not request.user_input.strip():
            messages.append({"role": "user", "content": "Hello"})
            logger.info("👋 No history or input – adding 'Hello' message")
        else:
            messages.extend(request.history)
            messages.append({"role": "user", "content": request.user_input})
            logger.info("🧠 Appended history and user input")

        logger.info("💬 Sending to GPT...")
        response = get_chat_completion(
            messages,
            tools=tool_descriptions,
            tool_choice="auto",
            return_raw=True
        )
        logger.info("✅ GPT responded")

        choice = response.choices[0]
        messages.append(choice.message)

        updated_inputs = {
            "hmo": request.hmo,
            "tier": request.tier,
            "confirmation": request.confirmed
        }

        if choice.finish_reason == "tool_calls":
            logger.info("🔧 Detected tool calls")

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                logger.info(f"⚙️ Handling tool: {tool_name} with args: {tool_args}")

                result = handle_tool_call(tool_name, tool_args)
                logger.info(f"📤 Tool result: {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

                try:
                    parsed = json.loads(result)
                    updated_inputs["hmo"] = parsed.get("hmo", updated_inputs["hmo"])
                    updated_inputs["tier"] = parsed.get("tier", updated_inputs["tier"])
                    updated_inputs["confirmation"] = parsed.get("confirmed", updated_inputs["confirmation"])
                except json.JSONDecodeError:
                    logger.warning("⚠️ JSON decode error from tool result")

            logger.info("🔁 Sending follow-up request to GPT")
            follow_up = get_chat_completion(
                messages,
                tools=tool_descriptions,
                tool_choice="auto",
                return_raw=True
            )
            follow_choice = follow_up.choices[0]
            messages.append(follow_choice.message)

            logger.info("✅ Returning response from follow-up GPT call")
            return {
                "response": follow_choice.message.content,
                "inputs": updated_inputs,
                "history": messages,
                "tool_results": [],
                "confirmed": updated_inputs.get("confirmation", "")
            }

        elif choice.finish_reason == "stop":
            logger.info("🛑 GPT finished without tool calls")
            return {
                "response": choice.message.content,
                "inputs": updated_inputs,
                "confirmed": updated_inputs.get("confirmation", "")
            }

    except Exception as e:
        logger.error(f"❌ Exception occurred: {e}")
        return {"response": f"❌ Internal server error: {str(e)}"}




@app.post("/phase_2")
async def phase_2(request: Phase2Request):
    try:
        logger.info("📥 Phase 2 request received")
        logger.info(f"HMO: {request.hmo}, Tier: {request.tier}, Lang: {request.lang}")
        logger.info(f"User question: {request.question}")

        hmo_norm, tier_norm = normalize_hmo_tier(request.hmo, request.tier)
        index, metadata = load_data()
        mask = filter_by_hmo_tier(metadata, hmo_norm, tier_norm)

        user_question = request.question
        if request.lang.lower() == "english":
            user_question = translate_to_hebrew(user_question)
            logger.info(f"Translated to Hebrew: {user_question}")

        query_vec = get_embedding(user_question)
        top_indices = get_top_matches(index, query_vec, mask, top_k=5)
        context_chunks = [metadata[i]["text"] for i in top_indices]
        answer = get_answer_from_metadata(user_question, context_chunks, request.hmo, request.tier, request.lang)

        return {"answer": answer}

    except Exception as e:
        logger.error(f"❌ Error in Phase 2: {e}")
        return {"answer": f"❌ Failed to generate answer: {str(e)}"}
