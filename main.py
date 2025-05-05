# main.py

import os
import json
from pathlib import Path
from logic.azure_calls import get_chat_completion, get_embedding
from tools import tool_descriptions, collect_hmo, collect_insurance_tier, confirm_information
from src.extract_data_embd import run_extraction
from src.embd_chunks import normalize_hmo_tier, load_data, get_top_matches, get_answer_from_metadata, filter_by_hmo_tier, build_and_save_index

def load_system_prompt(language: str) -> str:
    prompt_dir = Path(__file__).resolve().parent / "prompts"
    filename = "info_prompt_en.txt" if language == "en" else "info_prompt_he.txt"
    with open(prompt_dir / filename, "r", encoding="utf-8") as f:
        return f.read()

def translate_to_hebrew(text: str) -> str:
    messages = [
        {"role": "system", "content": "Translate the following question from English to Hebrew. Respond with Hebrew only."},
        {"role": "user", "content": text}
    ]
    response = get_chat_completion(messages)
    return response.strip()


def handle_tool_call(tool_name: str, arguments: str):
    data = json.loads(arguments)
    if tool_name == "collect_hmo":
        return collect_hmo(data["hmo"])
    elif tool_name == "collect_insurance_tier":
        return collect_insurance_tier(data["tier"])
    elif tool_name == "confirm_information":
        return confirm_information(data["confirmation"])
    return "Unknown tool call."

def run_phase_1(language: str):
    system_prompt = load_system_prompt(language)
    print("\n👩‍⚕️ BOT: Welcome! Let's get started collecting your information.")
    print("💬 You can type 'exit' anytime to stop.\n")

    messages = [{"role": "system", "content": system_prompt}]
    hmo, tier, confirmed = None, None, False

    # Let GPT start the conversation
    response = get_chat_completion(
        messages,
        tools=tool_descriptions,
        tool_choice="auto",
        return_raw=True
    )
    choice = response.choices[0]
    messages.append(choice.message)
    print(f"🤖 BOT: {choice.message.content}\n")

    while not confirmed:
        user_input = input("🧑 You: ").strip()
        if user_input.lower() == "exit":
            print("👋 Exiting...")
            return None

        messages.append({"role": "user", "content": user_input})

        response = get_chat_completion(
            messages,
            tools=tool_descriptions,
            tool_choice="auto",
            return_raw=True
        )
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            # ✅ Append assistant message with tool_calls
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments

                print(f"[🔧] Handling tool: {tool_name} with args: {tool_args}")

                result = handle_tool_call(tool_name, tool_args)

                # ✅ Append tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

                # Extract info if possible
                try:
                    data = json.loads(result)
                    print(f"[📥] Tool returned: {data}")

                    hmo = data.get("hmo", hmo)
                    tier = data.get("tier", tier)             

                    if data.get("confirmed") is True :
                        confirmed = True
                except json.JSONDecodeError:
                    pass

            # ✅ Now call GPT *once* after all tool responses are added
            follow_up = get_chat_completion(
                messages,
                tools=tool_descriptions,
                tool_choice="auto",
                return_raw=True
            )
            follow_choice = follow_up.choices[0]

            if follow_choice.finish_reason == "tool_calls":
                messages.append(follow_choice.message)
            else:
                follow_msg = follow_choice.message.content
                messages.append({"role": "assistant", "content": follow_msg})
                print(f"🤖 BOT: {follow_msg}\n")

        elif choice.finish_reason == "stop":
            bot_msg = choice.message.content
            messages.append({"role": "assistant", "content": bot_msg})
            print(f"🤖 BOT: {bot_msg}\n")

    print("✅ Info collection complete. Summary:")
    print(f"🏥 HMO: {hmo}")
    print(f"💎 Tier: {tier}")
    return {"hmo": hmo, "tier": tier, "confirmed": True}

def run_phase_2(hmo: str, tier: str, lang: str):
    print("\n🤖 BOT: You can now ask me questions about your medical services.")
    print("💬 Type 'exit' to stop.\n")

    
    # print("\n🔧Extracting structured text from HTML files...")
    # run_extraction()

    # print("\n⚙️  Generating embeddings and building FAISS index...")
    # build_and_save_index()

    # print("\n✅ Knowledge base is ready!")
    
    
    # Normalize HMO and tier to Hebrew
    hmo_norm, tier_norm = normalize_hmo_tier(hmo, tier)

    index, metadata = load_data()
    mask = filter_by_hmo_tier(metadata, hmo_norm, tier_norm)

    while True:
        user_question = input("🧑 You: ").strip()
        if user_question.lower() == "exit":
            print("👋 Goodbye!")
            break
        
        if lang == "en":
            user_question= translate_to_hebrew(user_question)  
            print(f"Translated Question: {user_question}")  

        query_vec = get_embedding(user_question)
        # print(f"\n🔍 Query Vector: {query_vec}")

        top_indices = get_top_matches(index, query_vec, mask, top_k=5)
        print(f"📄 Top Indices: {top_indices}")
        context_chunks = [metadata[i]["text"] for i in top_indices]

        answer = get_answer_from_metadata(user_question, context_chunks, hmo, tier)
        print(f"\n🤖 BOT: {answer}\n")


if __name__ == "__main__":
    lang_input = input("🌐 Choose a language (en/he): ").strip().lower()
    if lang_input not in ("en", "he"):
        print("⚠️ Invalid input. Defaulting to English.\n")
        lang_input = "en"

    user_info = run_phase_1(lang_input)
    print(f"user_info: {user_info}")

    if user_info and user_info.get("confirmed"):
        run_phase_2(user_info["hmo"], user_info["tier"], lang_input)
