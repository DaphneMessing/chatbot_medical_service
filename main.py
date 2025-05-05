# main.py

import os
import json
from pathlib import Path
from logic.azure_calls import get_chat_completion
from tools import tool_descriptions, collect_hmo, collect_insurance_tier, confirm_information

def load_system_prompt(language: str) -> str:
    prompt_dir = Path(__file__).resolve().parent / "prompts"
    filename = "info_prompt_en.txt" if language == "en" else "info_prompt_he.txt"
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
                    hmo = data.get("hmo", hmo)
                    tier = data.get("tier", tier)
                    if "✅" in data.get("message", ""):
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

if __name__ == "__main__":
    lang_input = input("🌐 Choose a language (en/he): ").strip().lower()
    if lang_input not in ("en", "he"):
        print("⚠️ Invalid input. Defaulting to English.\n")
        lang_input = "en"

    user_info = run_phase_1(lang_input)
