import streamlit as st
import google.generativeai as genai
import json
import time
import pandas as pd
from gtts import gTTS
from io import BytesIO
from datetime import datetime # <--- 1. 新增這個工具來抓日期

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="AI 英文隨身教練", page_icon="🎓")

st.title("🎓 AI 英文隨身教練")
st.markdown("這是一個讓你可以用「中英夾雜」練習口說的工具。")

# --- 2. 側邊欄：API Key 設定 ---
with st.sidebar:
    st.header("🔑 設定")
    user_api_key = st.text_input("請輸入 Google Gemini API Key", type="password")
    st.markdown("[👉 按此免費申請 API Key](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.caption("由 [您的名字] 開發設計")

# --- 3. 初始化 Session State (記憶體) ---
if "mistakes" not in st.session_state:
    st.session_state.mistakes = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. 核心函式：呼叫 AI ---
def get_ai_response(text, api_key):
    genai.configure(api_key=api_key)
    try:
        # 使用 Gemini 2.5 Flash 模型
        model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash", 
            generation_config={"response_mime_type": "application/json", "temperature": 0.7},
            system_instruction="""
            You are an enthusiastic English conversation coach.
            User speaks mixed Chinese/English.
            Output JSON:
            {
                "correction": "Correct English sentence",
                "explanation": "Explanation in Traditional Chinese",
                "reply": "Roleplay response in English",
                "reply_zh": "Chinese translation of reply"
            }
            """
        )
        response = model.generate_content(text)
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# --- 5. 核心函式：文字轉語音 ---
def text_to_audio(text):
    if not text: return None
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except:
        return None

# --- 6. 主畫面邏輯 ---

if not user_api_key:
    st.warning("👈 請先在左側欄位輸入您的 API Key 才能開始喔！")
else:
    # A. 顯示歷史訊息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "display_text" in msg:
                st.markdown(msg["display_text"])
            else:
                st.write(msg["content"])
            
            if "audio_reply" in msg and msg["audio_reply"]:
                st.caption("🔊 聽 AI 回應 (Reply):")
                st.audio(msg["audio_reply"], format='audio/mp3')
            
            if "audio_correction" in msg and msg["audio_correction"]:
                st.caption("🔊 聽正確說法 (Correction):")
                st.audio(msg["audio_correction"], format='audio/mp3')

    # B. 輸入框處理
    if user_input := st.chat_input("試著說：我想要 book 一個 table..."):
        # 顯示使用者輸入
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 呼叫 AI
        with st.spinner("AI 正在思考..."):
            ai_data = get_ai_response(user_input, user_api_key)

        # 處理結果
        if "error" in ai_data:
            st.error(f"發生錯誤: {ai_data['error']} (請檢查 API Key 或模型名稱)")
        else:
            reply_text = ai_data.get('reply', '')
            reply_zh = ai_data.get('reply_zh', '')
            correction = ai_data.get('correction', '')
            explanation = ai_data.get('explanation', '')
            
            audio_correction = text_to_audio(correction)
            audio_reply = text_to_audio(reply_text)
            
            display_text = f"""
            **🤖 回應:** {reply_text}
            *({reply_zh})*
            
            ---
            ✨ **修正:** `{correction}`
            
            💡 **點評:** {explanation}
            """

            with st.chat_message("assistant"):
                st.markdown(display_text)
                
                if audio_reply:
                    st.caption("🔊 聽 AI 回應 (Reply):")
                    st.audio(audio_reply, format='audio/mp3')

                if audio_correction:
                    st.caption("🔊 聽正確說法 (Correction):")
                    st.audio(audio_correction, format='audio/mp3')

            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply_text,
                "display_text": display_text,
                "audio_reply": audio_reply,
                "audio_correction": audio_correction
            })

            st.session_state.mistakes.append({
                "原句": user_input,
                "修正": correction,
                "解析": explanation,
                "AI回應": reply_text
            })

# --- 7. 下載按鈕區域 (修改處) ---
if st.session_state.mistakes:
    st.divider()
    df = pd.DataFrame(st.session_state.mistakes)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    
    # <--- 2. 這裡修改了檔名設定
    # 取得今天的日期，格式變成 YYYYMMDD (例如 20240101)
    today_str = datetime.now().strftime("%Y%m%d")
    file_name = f"my_english_mistakes_{today_str}.csv"
    
    st.download_button(
        label=f"📥 下載本次練習筆記 ({today_str})", # 按鈕文字也加上日期，看起來更直覺
        data=csv,
        file_name=file_name, # 設定新的檔名
        mime='text/csv',
    )
