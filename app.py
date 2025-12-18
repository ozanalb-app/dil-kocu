import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import json
import os
import random
import io
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="Iron Discipline Coach", page_icon="🛡️", layout="wide")

DATA_FILE = "user_data.json"

TOPIC_POOL = {
    "A2": ["Ordering Food", "Daily Routine", "Asking Directions", "Family & Friends", "Weekend Plans", "Shopping"],
    "B1": ["Job Interview", "Travel Problems", "Technology & Future", "Health Habits", "Hotel Complaints", "Social Media"],
    "B2": ["Global Warming", "Remote Work", "AI Ethics", "Cultural Differences", "Education Systems", "Economy"]
}

# --- 2. VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "current_level": "A2", 
            "lessons_completed": 0, 
            "exam_scores": [], 
            "vocabulary_bank": [], 
            "next_mode": "ASSESSMENT"
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

user_data = load_data()

# --- 3. DERS BAŞLATICI ---
def start_lesson_logic(client, level, mode, duration_mins):
    # 1. Konu ve Rol Seçimi
    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {level}. TOPIC: {topic}. GOAL: Test the user. NO help. Do not correct errors, just evaluate."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine A2/B1/B2 level. Ask 3 progressively harder questions. Start with a simple introduction question."
    else:
        topic = random.choice(TOPIC_POOL.get(level, ["General Conversation"]))
        system_role = f"ACT AS: Helpful Coach. LEVEL: {level}. TOPIC: {topic}. Keep conversation going. Correct major mistakes kindly."

    # 2. Hedef Kelimeleri Belirle
    target_vocab = []
    if mode == "LESSON":
        vocab_prompt = f"Generate 5 useful English words (JSON list of strings) related to '{topic}' for {level} level learner. Output ONLY valid JSON: ['word1', 'word2'...]"
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a JSON generator. Output only the JSON array."}, 
                    {"role": "user", "content": vocab_prompt}
                ]
            )
            content = res.choices[0].message.content
            if "```" in content: content = content.split("[")[1].split("]")[0]
            if "[" not in content: content = "[" + content + "]"
            target_vocab = json.loads(content)
        except:
            target_vocab = ["opinion", "suggest", "experience", "prefer", "describe"]

    # 3. Oturumu Başlat (Değişkenleri Kaydet)
    st.session_state.lesson_active = True
    st.session_state.start_time = time.time()
    st.session_state.target_duration = duration_mins * 60 # Saniyeye çevir
    st.session_state.target_vocab = target_vocab
    st.session_state.topic = topic
    
    final_prompt = f"{system_role}\nCONTEXT: The student must try to use these words: {', '.join(target_vocab)}.\nIf they use one, PRAISE them briefly inside parentheses."
    
    st.session_state.messages = [{"role": "system", "content": final_prompt}]
    
    # İlk Mesaj
    try:
        first_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_msg = first_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": first_msg})
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")

# --- 4. SOL PANEL (DASHBOARD) ---
with st.sidebar:
    st.title("🛡️ Öğrenci Kimliği")
    
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(label="Seviye", value=user_data['current_level'])
    with col_b:
        st.metric(label="Ders No", value=user_data['lessons_completed'] + 1)
    
    st.info(f"📚 **Kelime Hazinesi:** {len(user_data['vocabulary_bank'])} Kelime")

    st.write("---")
    if user_data["next_mode"] == "EXAM":
        st.error("⚠️ **DURUM: SINAV ZAMANI!**")
    elif user_data["next_mode"] == "ASSESSMENT":
        st.warning("⚠️ **DURUM: SEVİYE TESPİT**")
    else:
        completed_in_cycle = user_data['lessons_completed'] % 5
        kalan = 5 - completed_in_cycle
        st.write(f"🎯 **Sınava Kalan:** {kalan} Ders")
        st.progress(completed_in_cycle / 5.0)
    
    if st.session_state.get("lesson_active", False):
        st.divider()
        st.markdown("### ⏱️ Canlı Ders")
        st.success(f"**Konu:** {st.session_state.topic}")
        
        if st.session_state.target_vocab:
            st.warning("🔑 **Hedef Kelimeler:**")
            for word in st.session_state.target_vocab:
                st.markdown(f"- `{word}`")
        
        # ZAMAN SAYACI
        elapsed = int(time.time() - st.session_state.start_time)
        target = st.session_state.target_duration
        remaining = target - elapsed
        
        if remaining > 0:
            st.error(f"⏳ **Kalan:** {remaining // 60} dk {remaining % 60} sn")
        else:
            st.success("✅ **Süre Doldu!** Çıkabilirsin.")

    st.divider()
    with st.expander("Tehlikeli Bölge"):
        if st.button("TÜM İLERLEMEYİ SİL"):
            save_data({
                "current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT"
            })
            st.rerun()

# --- 5. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)

    st.title("⚔️ Iron Discipline Language Core")

    # A) DERS BAŞLAMADIYSA -> AYARLAR VE BAŞLAT
    if not st.session_state.get("lesson_active", False):
        st.markdown(f"### Hoş geldin! 👋")
        
        col_info, col_set = st.columns([2, 1])
        
        with col_info:
            st.info(f"📍 **Seviye:** {user_data['current_level']} | **Mod:** {user_data['next_mode']}")
            st.write("Ders süresini seç ve başla. Süre dolmadan çıkış yapamazsın!")

        with col_set:
            # SÜRE AYARI (SLIDER)
            selected_duration = st.slider("⏳ Ders Süresi (Dakika)", min_value=1, max_value=30, value=10, step=1)
        
        st.write("")
        btn_label = "🚀 DERSİ BAŞLAT" if user_data["next_mode"] != "EXAM" else "🔥 SINAVI BAŞLAT"
        
        if st.button(btn_label, type="primary", use_container_width=True):
            with st.spinner("Yapay Zeka Hazırlanıyor..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], selected_duration)
                st.rerun()

    # B) DERS AKTİFSE -> SOHBET
    else:
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] != "system":
                    avatar = "🤖" if msg["role"] == "assistant" else "👤"
                    with st.chat_message(msg["role"], avatar=avatar):
                        st.write(msg["content"])

        st.write("---")
        col_mic, col_finish = st.columns([1, 4])
        
        with col_mic:
            audio = mic_recorder(start_prompt="🎤 KONUŞ", stop_prompt="⏹️ GÖNDER", key="recorder")
        
        with col_finish:
            elapsed_sec = time.time() - st.session_state.start_time
            target_sec = st.session_state.target_duration
            
            if st.button("🏁 DERSİ BİTİR / FINISH", use_container_width=True):
                # ZAMAN KİLİDİ
                if user_data["next_mode"] != "ASSESSMENT" and elapsed_sec < target_sec:
                    missing = target_sec - elapsed_sec
                    st.toast("🚫 ÇIKIŞ YASAK!", icon="🔒")
                    st.error(f"Disiplin! Daha {int
