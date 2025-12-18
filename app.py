import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS # YENİ KÜTÜPHANE
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
    # Konu Seçimi
    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {level}. TOPIC: {topic}. GOAL: Test the user. NO help."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions."
    else:
        topic = random.choice(TOPIC_POOL.get(level, ["General Conversation"]))
        system_role = f"ACT AS: Helpful Coach. LEVEL: {level}. TOPIC: {topic}. Keep conversation going."

    # Hedef Kelimeler
    target_vocab = []
    if mode == "LESSON":
        vocab_prompt = f"Generate 5 useful English words (JSON list) related to '{topic}' for {level} level. Output ONLY JSON."
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": vocab_prompt}]
            )
            content = res.choices[0].message.content
            if "```" in content: content = content.split("[")[1].split("]")[0]
            if "[" not in content: content = "[" + content + "]"
            target_vocab = json.loads(content)
        except:
            target_vocab = ["opinion", "suggest", "experience", "prefer", "describe"]

    # Değişkenleri Kaydet
    st.session_state.lesson_active = True
    st.session_state.start_time = time.time()
    st.session_state.target_duration = duration_mins * 60
    st.session_state.target_vocab = target_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    
    final_prompt = f"{system_role}\nCONTEXT: The student must try to use these words: {', '.join(target_vocab)}.\nIf they use one, PRAISE them briefly."
    
    st.session_state.messages = [{"role": "system", "content": final_prompt}]
    
    # İlk Mesaj
    try:
        first_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_msg = first_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        # SES ÜRET (gTTS)
        tts = gTTS(text=first_msg, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        st.session_state.last_audio_response = audio_fp.getvalue() # Sesi kaydet
        
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")

# --- 4. ARAYÜZ ---
with st.sidebar:
    st.title("🛡️ Öğrenci Kimliği")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a: st.metric("Seviye", user_data['current_level'])
    with col_b: st.metric("Ders No", user_data['lessons_completed'] + 1)
    
    st.info(f"📚 **Kelime:** {len(user_data['vocabulary_bank'])}")
    st.write("---")
    
    if user_data["next_mode"] == "EXAM": st.error("⚠️ **SINAV ZAMANI!**")
    elif user_data["next_mode"] == "ASSESSMENT": st.warning("⚠️ **SEVİYE TESPİT**")
    else:
        prog = (user_data['lessons_completed'] % 5) / 5.0
        st.write(f"🎯 **Sınava Kalan:** {5 - (user_data['lessons_completed'] % 5)} Ders")
        st.progress(prog)
    
    if st.session_state.get("lesson_active", False):
        st.divider()
        st.success(f"**Konu:** {st.session_state.topic}")
        if st.session_state.target_vocab:
            st.warning("🔑 **Kelimeler:**")
            for w in st.session_state.target_vocab: st.markdown(f"- `{w}`")
        
        elapsed = int(time.time() - st.session_state.start_time)
        remain = st.session_state.target_duration - elapsed
        if remain > 0: st.error(f"⏳ **Kalan:** {remain//60} dk {remain%60} sn")
        else: st.success("✅ **Süre Doldu!**")

    st.divider()
    with st.expander("Tehlikeli Bölge"):
        if st.button("TÜM İLERLEMEYİ SİL"):
            save_data({"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT"})
            st.rerun()

# --- 5. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    st.title("🌱 Eco Discipline Language Core")

    # A) DERS SEÇİMİ
    if not st.session_state.get("lesson_active", False):
        st.markdown("### Hoş geldin! 👋")
        c1, c2 = st.columns([2,1])
        with c1: st.info(f"📍 **Mod:** {user_data['next_mode']}")
        with c2: duration = st.slider("⏳ Süre (Dk)", 1, 30, 10)
        
        btn = "🚀 BAŞLAT" if user_data["next_mode"] != "EXAM" else "🔥 SINAV"
        if st.button(btn, type="primary", use_container_width=True):
            with st.spinner("Hazırlanıyor..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], duration)
                st.rerun()

    # B) SOHBET EKRANI
    else:
        # Mesajları Yazdır
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
                    st.write(msg["content"])
        
        # SESLENDİRME (MP3 ÇALAR)
        if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
            # Autoplay=True ile otomatik çalmayı dener
            st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)
            # Not: Sesi sıfırlamıyoruz (None yapmıyoruz) ki player ekranda kalsın

        st.write("---")
        c_mic, c_fin = st.columns([1, 4])
        
        with c_mic:
            audio = mic_recorder(start_prompt="🎤 KONUŞ", stop_prompt="⏹️ GÖNDER", key="recorder")
        
        with c_fin:
            elapsed = time.time() - st.session_state.start_time
            if st.button("🏁 DERSİ BİTİR", use_container_width=True):
                if user_data["next_mode"] != "ASSESSMENT" and elapsed < st.session_state.target_duration:
                    st.toast("🚫 SÜRE DOLMADI!", icon="🔒")
                else:
                    st.session_state.lesson_active = False 
                    with st.spinner("Analiz Yapılıyor..."):
                        # Analiz Mantığı
                        analysis_prompt = "ANALYZE session. OUTPUT ONLY JSON: {'score': 0-100, 'learned_words': [], 'level_recommendation': 'Stay/Up'}"
                        msgs = st.session_state.messages + [{"role": "system", "content": analysis_prompt}]
                        try:
                            res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                            rep = json.loads(res.choices[0].message.content.replace("```json","").replace("```",""))
                            
                            user_data["lessons_completed"] += 1
                            if "learned_words" in rep: user_data["vocabulary_bank"].extend(rep["learned_words"])
                            
                            if user_data["next_mode"] == "ASSESSMENT":
                                user_data["current_level"] = "B1" if "Up" in rep.get("level_recommendation","") else "A2"
                                user_data["next_mode"] = "LESSON"
                            elif user_data["lessons_completed"] % 5 == 0:
                                user_data["next_mode"] = "EXAM"
                            elif user_data["next_mode"] == "EXAM":
                                if rep.get("score", 0) >= 75: 
                                    user_data["current_level"] = "B1" if user_data["current_level"]=="A2" else "B2"
                                user_data["next_mode"] = "LESSON"
                            else:
                                user_data["next_mode"] = "LESSON"
                                
                            save_data(user_data)
                            st.success("Kaydedildi!")
                            st.json(rep)
                        except: st.error("Analiz hatası.")
                        if st.button("Devam"): st.rerun()

        # SES İŞLEME
        if audio:
            if "last_audio_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_audio_bytes:
                st.session_state.last_audio_bytes = audio['bytes']
                
                with st.spinner("Dinliyor..."):
                    try:
                        # 1. Whisper
                        audio_bio = io.BytesIO(audio['bytes'])
                        audio_bio.name = "audio.webm"
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", file=audio_bio, language="en"
                        ).text
                        st.session_state.messages.append({"role": "user", "content": transcript})
                        
                        # 2. GPT
                        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                        reply = res.choices[0].message.content
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        
                        # 3. gTTS (Bedava Ses Oluşturucu)
                        tts = gTTS(text=reply, lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        st.session_state.last_audio_response = audio_fp.getvalue()
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hata: {e}")
else:
    st.warning("API Key Giriniz")
