#app.py

import streamlit as st
import requests
import json

API_URL_PHASE_1 = "http://localhost:8000/phase_1"  
API_URL_PHASE_2 = "http://localhost:8000/phase_2"  

st.title("🩺 HMO Medical Assistant")

if "language" not in st.session_state:
    st.session_state.language = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {"hmo": "", "tier": "", "confirmation": ""}
if "history" not in st.session_state:
    st.session_state.history = []
if "language_selected" not in st.session_state:
    st.session_state.language_selected = False

# Select Language
if not st.session_state.language_selected:
    lang_option = st.selectbox("Choose Language/ בחר שפה", ["Select", "en", "he"])
    if lang_option != "Select":
        st.session_state.language = lang_option
        st.session_state.language_selected = True
        st.rerun()
        
if st.session_state.language_selected and not st.session_state.history:
    try:
        response = requests.post(API_URL_PHASE_1, json={
            "language": st.session_state.language,
            "user_input": "start",
            "hmo": "",
            "tier": "",
            "confirmed": "",
            "history": []

        })

        result = response.json()

        assistant_reply = result.get("response", "⚠️ No response from server.")
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})   


    except Exception as e:
        st.session_state.history.append(
            {"role": "assistant", "content": f"❌ Error: {e}"}
        )


# Chat Interface (Phase 1 or 2 depending on confirmation)
if st.session_state.language_selected:
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    
    user_input = st.chat_input("Enter your message...")

    if user_input:
        st.session_state.history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if st.session_state.inputs.get("confirmation") is True:
            # PHASE 2: Ask about medical services
            try:
                phase2_response = requests.post(API_URL_PHASE_2, json={
                    "hmo": st.session_state.inputs.get("hmo", ""),
                    "tier": st.session_state.inputs.get("tier", ""),
                    "lang": st.session_state.language,
                    "question": user_input
                })
                phase2_data = phase2_response.json()
                assistant_reply = phase2_data.get("answer", "⚠️ No answer received.")

            except Exception as e:
                assistant_reply = f"❌ Error calling phase 2: {e}"

            

        else:
            # Phase 1: Continue information collection
            try:
                response = requests.post(API_URL_PHASE_1, json={
                    "language": st.session_state.language,
                    "hmo": st.session_state.inputs["hmo"],
                    "tier": st.session_state.inputs["tier"],
                    "confirmed": st.session_state.inputs["confirmation"],
                    "user_input": user_input,
                    "history": st.session_state.history[:-1]
                })
                result = response.json()
                assistant_reply = result.get("response", "⚠️ No response from server.")

                try:
                    # Set from the backend directly
                    st.session_state.inputs = result.get("inputs", st.session_state.inputs)

                    #update the confirmation state based on the response
                    if "confirmed" in result:
                        st.session_state.inputs["confirmation"] = result["confirmed"]

                    # Show assistant message (may be plain string)
                    assistant_reply = result.get("response", "⚠️ No response from server.")

                except Exception as e:
                    assistant_reply = f"❌ Error parsing response: {e}"


            except Exception as e:
                assistant_reply = f"❌ Error: {e}"

        st.session_state.history.append({"role": "assistant", "content": assistant_reply})
        with st.chat_message("assistant"):
            st.markdown(assistant_reply)

