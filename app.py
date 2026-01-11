import streamlit as st
import google.generativeai as genai
import json
import time
import pandas as pd # 用來處理表格與下載
from gtts import gTTS
from io import BytesIO

# --- 頁面設定 ---
st.set_page_config(page_title="AI 英文隨身教練", page_icon="🎓")

st.title("🎓 AI 英文隨身教練")
st.markdown("這是一個讓你可以用「中英夾雜」練習口說的工具。")

# --- 1. 側邊欄：讓學生輸入 API Key ---
with st.sidebar:
    st.header("🔑 設定")
    user_api_key = st.text_input("請輸入 Google Gemini API Key", type="password")
    st.markdown("[👉 按此免費申請 API Key](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    st.markdown("### 關於這個 App")
    st.caption("由 [您的名字] 開發設計")

# --- 初始化 Session State (用來暫存錯題本) ---
if "mistakes" not in st.session_state:
    st.session_state.mistakes = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 核心功能函式 ---
def get_ai_response(text, api_key):
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # 使用 Flash 模型速度快且省錢
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

def text_to_audio(text):
    if not text: return None
    try:
        tts = gTTS(text=text, lang='en')
        # 將音訊存入記憶體 (BytesIO)，不要存成檔案，這樣在網頁上跑比較快且安全
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# --- 主畫面邏輯 ---

# 檢查是否有輸入 Key
if not user_api_key:
    st.warning("👈 請先在左側欄位輸入您的 API Key 才能開始喔！")
else:
    # 顯示對話紀錄
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "audio" in msg and msg["audio"]:
                st.audio(msg["audio"], format='audio/mp3')

    # 輸入框
    if user_input := st.chat_input("試著說：我想要 book 一個 table..."):
        # 1. 顯示使用者輸入
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # 2. 呼叫 AI
        with st.spinner("AI 正在思考..."):
            ai_data = get_ai_response(user_input, user_api_key)

        if "error" in ai_data:
            st.error(f"發生錯誤: {ai_data['error']} (請檢查 API Key 是否正確)")
        else:
            # 3. 處理回應
            reply_text = ai_data.get('reply', '')
            correction = ai_data.get('correction', '')
            explanation = ai_data.get('explanation', '')
            
            # 生成語音
            audio_fp = text_to_audio(correction)
            
            # 顯示 AI 回應
            with st.chat_message("assistant"):
                st.write(f"**🤖 回應:** {reply_text}")
                st.info(f"✨ **修正:** {correction}\n\n💡 **點評:** {explanation}")
                if audio_fp:
                    st.audio(audio_fp, format='audio/mp3')

            # 存入歷史紀錄
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"{reply_text}\n(修正: {correction})",
                "audio": audio_fp
            })

            # 4. 自動加入錯題本 (存入暫存記憶體)
            st.session_state.mistakes.append({
                "原句": user_input,
                "修正": correction,
                "解析": explanation,
                "AI回應": reply_text
            })

# --- 下載錯題本功能 (取代 Google Sheets) ---
if st.session_state.mistakes:
    st.divider()
    st.subheader("📝 你的錯題筆記本")
    df = pd.DataFrame(st.session_state.mistakes)
    st.dataframe(df) # 顯示表格
    
    # 轉換成 CSV
    csv = df.to_csv(index=False).encode('utf-8-sig') # utf-8-sig 才能讓 Excel 正常顯示中文
    
    st.download_button(
        label="📥 下載筆記本 (CSV)",
        data=csv,
        file_name='my_english_mistakes.csv',
        mime='text/csv',
    )