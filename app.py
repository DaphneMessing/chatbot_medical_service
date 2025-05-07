
import streamlit as st
import requests
import json

API_URL = "http://localhost:8000/phase_1"  # Adjust if hosted elsewhere

st.title("🩺 HMO Medical Assistant")

if "language" not in st.session_state:
    st.session_state.language = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {"hmo": "", "tier": "", "confirmation": ""}
if "history" not in st.session_state:
    st.session_state.history = []
if "language_selected" not in st.session_state:
    st.session_state.language_selected = False


# Step 1: Select Language
if not st.session_state.language_selected:
    lang_option = st.selectbox("Choose Language/ בחר שפה", ["Select", "en", "he"])
    if lang_option != "Select":
        st.session_state.language = lang_option
        st.session_state.language_selected = True
        st.rerun()
        
if st.session_state.language_selected and not st.session_state.history:
    try:
        response = requests.post(API_URL, json={
            "language": st.session_state.language,
            "user_input": "start",
            "hmo": "",
            "tier": "",
            "confirmed": "",
            "history": []

        })

        result = response.json()

        st.write("🔍 Raw response from server:")
        st.write(result)

        assistant_reply = result.get("response", "⚠️ No response from server.")
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})   


    except Exception as e:
        st.session_state.history.append(
            {"role": "assistant", "content": f"❌ Error: {e}"}
        )


# Step 2: Chat Interface
if st.session_state.language_selected:
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if user_input := st.chat_input("Enter your message..."):
        st.session_state.history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

    try:
        response = requests.post(API_URL, json={
            "language": st.session_state.language,
            "hmo": st.session_state.inputs["hmo"],
            "tier": st.session_state.inputs["tier"],
            "confirmed": st.session_state.inputs["confirmation"],
            "user_input": user_input,
            "history": st.session_state.history[:-1]
        })
        result = response.json()
        
        st.write("🔍 Raw response from server:")
        st.write(result)

        assistant_reply = result.get("response", "⚠️ No response from server.")
        try:
            replay_data= json.loads(assistant_reply)
            assistant_reply = replay_data.get("message", assistant_reply)

            if replay_data.get("hmo"): 
                st.session_state.inputs["hmo"] = replay_data["hmo"]

            if replay_data.get("tier"):    
                st.session_state.inputs["tier"] = replay_data["tier"]

            if replay_data.get("confirmed"):
                st.session_state.inputs["confirmation"] = replay_data["confirmation"]


            st.session_state.inputs = result["inputs"]
        
        except json.JSONDecodeError:
            pass  # fallback to plain message if not JSON    
    except Exception as e:
        assistant_reply = f"❌ Error: {e}"

    st.session_state.history.append({"role": "assistant", "content": assistant_reply})
    with st.chat_message("assistant"):
        st.markdown(assistant_reply)
