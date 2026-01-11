import streamlit as st
import google.generativeai as genai
import json
import time
import pandas as pd
from gtts import gTTS
from io import BytesIO

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
        # 使用您指定的 Gemini 2.5 Flash 模型
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

# --- 5. 核心函式：文字轉語音 (不存檔，直接轉 Bytes) ---
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

# 如果沒有 Key，鎖住畫面
if not user_api_key:
    st.warning("👈 請先在左側欄位輸入您的 API Key 才能開始喔！")
else:
    # A. 顯示歷史訊息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # 顯示文字
            if "display_text" in msg:
                st.markdown(msg["display_text"])
            else:
                st.write(msg["content"])
            
            # 顯示歷史語音 (如果有的話)
            if "audio_reply" in msg and msg["audio_reply"]:
                st.caption("🔊 聽 AI 回應 (Reply):")
                st.audio(msg["audio_reply"], format='audio/mp3')
            
            if "audio_correction" in msg and msg["audio_correction"]:
                st.caption("🔊 聽正確說法 (Correction):")
                st.audio(msg["audio_correction"], format='audio/mp3')

    # B. 輸入框處理
    if user_input := st.chat_input("試著說：我想要 book 一個 table..."):
        # 1. 顯示使用者輸入
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 2. 呼叫 AI
        with st.spinner("AI 正在思考..."):
            ai_data = get_ai_response(user_input, user_api_key)

        # 3. 處理結果
        if "error" in ai_data:
            st.error(f"發生錯誤: {ai_data['error']} (請檢查 API Key 或模型名稱)")
        else:
            # 解析 JSON
            reply_text = ai_data.get('reply', '')
            reply_zh = ai_data.get('reply_zh', '')
            correction = ai_data.get('correction', '')
            explanation = ai_data.get('explanation', '')
            
            # 生成兩個語音檔
            audio_correction = text_to_audio(correction)
            audio_reply = text_to_audio(reply_text)
            
            # 組合顯示用的文字 Markdown
            display_text = f"""
            **🤖 回應:** {reply_text}
            *({reply_zh})*
            
            ---
            ✨ **修正:** `{correction}`
            
            💡 **點評:** {explanation}
            """

            # 顯示 AI 回應區塊
            with st.chat_message("assistant"):
                st.markdown(display_text)
                
                # 播放器 1: AI 回應
                if audio_reply:
                    st.caption("🔊 聽 AI 回應 (Reply):")
                    st.audio(audio_reply, format='audio/mp3')

                # 播放器 2: 正確說法
                if audio_correction:
                    st.caption("🔊 聽正確說法 (Correction):")
                    st.audio(audio_correction, format='audio/mp3')

            # 4. 存入歷史紀錄 (包含語音物件)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply_text,
                "display_text": display_text,
                "audio_reply": audio_reply,
                "audio_correction": audio_correction
            })

            # 5. 自動加入錯題本
            st.session_state.mistakes.append({
                "原句": user_input,
                "修正": correction,
                "解析": explanation,
                "AI回應": reply_text
            })

# --- 7. 下載按鈕區域 ---
if st.session_state.mistakes:
    st.divider()
    df = pd.DataFrame(st.session_state.mistakes)
    # 轉成 CSV (加上 BOM 防止中文亂碼)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 下載本次練習筆記 (CSV)",
        data=csv,
        file_name='my_english_mistakes.csv',
        mime='text/csv',
    )
    
