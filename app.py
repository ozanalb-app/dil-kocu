import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import json
import os
import random
import io
import time
import re

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pro Coach V3", page_icon="🎓", layout="wide")
DATA_FILE = "user_data.json"

TOPIC_POOL = {
    "A2": ["Ordering Food", "Daily Routine", "Asking Directions", "Family & Friends", "Weekend Plans", "Shopping"],
    "B1": ["Job Interview", "Travel Problems", "Technology & Future", "Health Habits", "Hotel Complaints", "Social Media"],
    "B2": ["Global Warming", "Remote Work", "AI Ethics", "Cultural Differences", "Education Systems", "Economy"]
}

# --- 2. YARDIMCI FONKSİYONLAR ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT"}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 🔥 YENİ: Akıllı JSON Ayıklayıcı (Hata Önleyici)
def strict_json_parse(text):
    try:
        # Metnin içindeki ilk { ve son } arasını bulur
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except:
        return {} # Hata olursa boş döndür ama çökme

user_data = load_data()

# --- 3. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, duration_mins):
    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {level}. TOPIC: {topic}. GOAL: Test the user. NO help."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions."
    else:
        topic = random.choice(TOPIC_POOL.get(level, ["General"]))
        system_role = f"ACT AS: Helpful Coach. LEVEL: {level}. TOPIC: {topic}. Keep conversation going."

    target_vocab = []
    # Kelime seçimi (Basit ve Hızlı)
    if mode == "LESSON":
        if level == "A2": target_vocab = ["happy", "go", "friend", "time", "good"]
        elif level == "B1": target_vocab = ["opinion", "suggest", "experience", "prefer", "describe"]
        else: target_vocab = ["perspective", "implie", "consequence", "debate", "theory"]

    st.session_state.lesson_active = True
    st.session_state.start_time = time.time()
    st.session_state.target_duration = duration_mins * 60
    st.session_state.target_vocab = target_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    
    # Prompt Hazırlığı
    final_prompt = f"{system_role}\nCONTEXT: The student must try to use these words: {', '.join(target_vocab)}.\nIf they use one, PRAISE them briefly."
    st.session_state.messages = [{"role": "system", "content": final_prompt}]
    
    # İlk Mesaj
    try:
        first_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_msg = first_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        # Seslendirme
        tts = gTTS(text=first_msg, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        st.session_state.last_audio_response = audio_fp.getvalue()
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")

# --- 4. ARAYÜZ ---
with st.sidebar:
    st.title("🎓 Pro Coach V3")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("API Key", type="password")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: st.metric("Seviye", user_data['current_level'])
    with c2: st.metric("Ders", user_data['lessons_completed'] + 1)
    
    st.info(f"📚 Kelime: {len(user_data['vocabulary_bank'])}")
    
    if st.session_state.get("lesson_active", False):
        st.divider()
        st.success(f"**Konu:** {st.session_state.topic}")
        if st.session_state.target_vocab:
            st.warning(f"**Hedef:** {', '.join(st.session_state.target_vocab)}")
            
        elapsed = int(time.time() - st.session_state.start_time)
        remain = st.session_state.target_duration - elapsed
        if remain > 0: st.info(f"⏳ **Kalan:** {remain//60} dk {remain%60} sn")
        else: st.success("✅ **Süre Doldu!**")

    st.divider()
    if st.button("RESET DATA"):
        save_data({"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT"})
        st.rerun()

# --- 5. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    st.title("🎧 High-Accuracy AI Coach")

    if not st.session_state.get("lesson_active", False):
        st.markdown(f"### Merhaba! Mod: **{user_data['next_mode']}**")
        dur = st.slider("Süre (Dk)", 1, 30, 10)
        btn = "🚀 BAŞLAT" if user_data["next_mode"] != "EXAM" else "🔥 SINAV"
        
        if st.button(btn, type="primary", use_container_width=True):
            with st.spinner("Hazırlanıyor..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], dur)
                st.rerun()
    else:
        # Sohbet Geçmişi
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
                    st.write(msg["content"])
        
        # Ses Çalar
        if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
            st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

        st.write("---")
        c_mic, c_fin = st.columns([1, 4])
        
        with c_mic:
            audio = mic_recorder(start_prompt="🎤 KONUŞ", stop_prompt="⏹️ GÖNDER", key="recorder")
        
        with c_fin:
            elapsed = time.time() - st.session_state.start_time
            if st.button("🏁 DERSİ BİTİR", use_container_width=True):
                # Erken Çıkış Kontrolü
                if user_data["next_mode"] != "ASSESSMENT" and elapsed < st.session_state.target_duration:
                    st.toast("🚫 SÜRE DOLMADI!", icon="🔒")
                else:
                    st.session_state.lesson_active = False 
                    with st.spinner("Analiz Yapılıyor..."):
                        # Analiz Promptu
                        analysis_prompt = "ANALYZE session. OUTPUT ONLY JSON: {'score': 0-100, 'learned_words': [], 'level_recommendation': 'Stay/Up'}"
                        msgs = st.session_state.messages + [{"role": "system", "content": analysis_prompt}]
                        try:
                            res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                            # 🔥 YENİ: Akıllı JSON Temizleme
                            rep = strict_json_parse(res.choices[0].message.content)
                            
                            if not rep: # Eğer boş geldiyse
                                rep = {"score": 80, "level_recommendation": "Stay"} # Varsayılan değer
                                st.error("Analiz formatı bozuk geldi ama ders sayıldı.")

                            user_data["lessons_completed"] += 1
                            if "learned_words" in rep: user_data["vocabulary_bank"].extend(rep["learned_words"])
                            
                            # Mod Geçişleri
                            if user_data["next_mode"] == "ASSESSMENT":
                                rec = rep.get("level_recommendation", "A2")
                                user_data["current_level"] = "B1" if "Up" in rec else "A2"
                                user_data["next_mode"] = "LESSON"
                                st.balloons()
                            elif user_data["lessons_completed"] % 5 == 0:
                                user_data["next_mode"] = "EXAM"
                            elif user_data["next_mode"] == "EXAM":
                                if rep.get("score", 0) >= 75:
                                    # Basit seviye artışı
                                    user_data["current_level"] = "B1" if user_data["current_level"]=="A2" else "B2"
                                    st.balloons()
                                user_data["next_mode"] = "LESSON"
                            else:
                                user_data["next_mode"] = "LESSON"
                                
                            save_data(user_data)
                            st.success("Ders Başarıyla Kaydedildi!")
                            st.json(rep)
                        except Exception as e:
                            st.error(f"Kritik Analiz Hatası: {e}")
                        
                        if st.button("Ana Menü"): st.rerun()

        # SES İŞLEME (WHISPER + CONTEXT)
        if audio:
            if "last_audio_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_audio_bytes:
                st.session_state.last_audio_bytes = audio['bytes']
                
                with st.spinner("Netleştiriliyor..."):
                    try:
                        audio_bio = io.BytesIO(audio['bytes'])
                        audio_bio.name = "audio.webm"
                        
                        # 🔥 YENİ: WHISPER'A İPUCU VERİYORUZ (Prompting)
                        # Bu satır, modelin konuyu bilmesini ve doğru anlamasını sağlar.
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_bio, 
                            language="en",
                            prompt=f"This is an English lesson about {st.session_state.topic}. The user level is {user_data['current_level']}."
                        ).text
                        
                        st.session_state.messages.append({"role": "user", "content": transcript})
                        
                        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                        reply = res.choices[0].message.content
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        
                        tts = gTTS(text=reply, lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        st.session_state.last_audio_response = audio_fp.getvalue()
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
else:
    st.warning("Lütfen API Anahtarını girin.")
