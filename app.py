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
st.set_page_config(page_title="Pınar's Friend", page_icon="🎤", layout="wide")
DATA_FILE = "user_data.json"

# WHISPER'IN UYDURDUĞU YASAKLI CÜMLELER (HALLUCINATION LIST)
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching", 
    "Copyright", "Subscribe", "Amara.org", "You", "you"
]

# --- KONU HAVUZU ---
TOPIC_POOL = {
    "A2": [
        "My Daily Morning Routine", "What I Do in the Evening", "Ordering Food at a Restaurant",
        "Asking for Directions in a City", "Shopping for Clothes", "Buying Food at the Supermarket",
        "My Favorite Food", "My Favorite Movie", "My Favorite Music", "My Best Friend", "My Family",
        "My Job or Daily Responsibilities", "My Hobbies and Free Time", "Plans for Next Weekend",
        "My Favorite Place in My City", "Talking About the Weather", "My House or Apartment",
        "A Typical Day at Home", "Going to the Doctor", "Taking Public Transport",
        "Ordering Coffee at a Café", "Talking About My Pet", "My Favorite Holiday",
        "My Favorite School Subject", "Talking About My Childhood", "A Simple Phone Call",
        "Making an Appointment", "Talking About Today", "What I Like and Don’t Like",
        "Daily Problems at Home"
    ],
    "B1": [
        "Describing a Past Holiday", "A Job Interview Simulation", "Solving a Problem at a Hotel",
        "Talking About My Workday", "Healthy Eating Habits", "My Hobbies and Why I Like Them",
        "Social Media: Good or Bad?", "Advice for a Tourist", "Learning a New Skill",
        "Technology in Daily Life", "A Problem with Online Shopping", "Talking About My Education",
        "Comparing Life Now and in the Past", "Living in a Foreign Country", "Describing a Difficult Day",
        "Making a Complaint Politely", "Giving Advice to a Friend", "Talking About Future Plans",
        "Using Technology at Work", "A Problem with a Neighbor", "Describing a Personal Achievement",
        "Work–Life Balance", "Talking About Health Problems", "A Problem at the Airport",
        "Discussing Weekend Activities", "Describing a Book or Series", "Advantages and Disadvantages of City Life",
        "Talking About Rules and Responsibilities", "Handling a Small Conflict", "My Opinion About Online Education"
    ],
    "B2": [
        "The Pros and Cons of Remote Work", "Climate Change and Global Warming", "Artificial Intelligence and Ethics",
        "Cultural Differences in Business", "Education System Reform", "Economic Challenges in Modern Society",
        "The Impact of Globalization", "Technology and Privacy", "Workplace Communication Problems",
        "Leadership Styles in Organizations", "Gender Equality at Work", "The Future of Education",
        "Social Media and Mental Health", "The Role of Governments in Society", "Balancing Career and Family Life",
        "Advantages and Risks of Artificial Intelligence", "Cultural Adaptation in a New Country",
        "Ethical Problems in Technology", "Remote Work vs Office Work", "The Importance of Lifelong Learning",
        "Consumerism and Modern Life", "Environmental Responsibility of Companies", "Freedom of Speech",
        "Global Economic Inequality", "Stress and Burnout at Work", "Decision Making Under Pressure",
        "Immigration and Integration", "The Role of Technology in Education", "Crisis Management",
        "The Future of Work"
    ]
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

def strict_json_parse(text):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except:
        return {}

user_data = load_data()

# --- 3. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_seconds):
    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {level}. TOPIC: {topic}. GOAL: Test user. RESPONSE STYLE: Short, direct questions. No long explanations."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions. RESPONSE STYLE: Very short."
    else:
        topic = random.choice(TOPIC_POOL.get(level, ["General"]))
        system_role = f"ACT AS: Helpful Coach. LEVEL: {level}. TOPIC: {topic}. RESPONSE STYLE: Keep answers UNDER 2 SENTENCES. Ask ONE question at a time."

    target_vocab = []
    
    if mode == "LESSON":
        full_vocab_list = []
        if level == "A2":
            full_vocab_list = [
                "happy", "sad", "angry", "tired", "hungry", "friend", "family", "child", "people", "person",
                "home", "house", "room", "kitchen", "bedroom", "work", "job", "school", "teacher", "student",
                "morning", "afternoon", "evening", "night", "today", "yesterday", "tomorrow", "weekend", "holiday", "time",
                "food", "breakfast", "lunch", "dinner", "coffee", "water", "restaurant", "shop", "market", "money",
                "travel", "bus", "train", "car", "walk", "city", "street", "park", "place", "country",
                "weather", "sunny", "rainy", "cold", "hot", "music", "movie", "book", "game", "hobby",
                "like", "love", "want", "need", "have", "go", "come", "make", "do", "see",
                "good", "bad", "easy", "difficult", "important", "help", "problem", "question", "answer", "idea",
                "everyday", "sometimes", "always", "usually", "never"
            ]
        elif level == "B1":
            full_vocab_list = [
                "opinion", "experience", "suggest", "prefer", "describe", "explain", "compare", "decide", "choose", "discuss",
                "problem", "solution", "reason", "result", "example", "recently", "usually", "generally", "sometimes", "currently",
                "challenge", "opportunity", "improve", "develop", "change", "habit", "routine", "lifestyle", "health", "balance",
                "education", "career", "interview", "responsibility", "skill", "technology", "internet", "application", "online", "digital",
                "travel", "culture", "difference", "similarity", "tradition", "environment", "pollution", "recycle", "energy", "nature",
                "communication", "relationship", "conflict", "agreement", "support", "advantage", "disadvantage", "benefit", "risk", "effect",
                "future", "plan", "goal", "decision", "expectation", "feel", "believe", "think", "agree", "disagree",
                "manage", "organize", "handle", "solve", "prepare", "situation", "experience", "opinion", "example", "point"
            ]
        else: # B2
            full_vocab_list = [
                "perspective", "viewpoint", "attitude", "belief", "assumption", "imply", "indicate", "suggest", "demonstrate", "highlight",
                "consequence", "outcome", "impact", "effect", "implication", "debate", "argument", "discussion", "controversy", "issue",
                "theory", "concept", "principle", "framework", "approach", "significant", "crucial", "essential", "relevant", "substantial",
                "analyze", "evaluate", "assess", "examine", "interpret", "compare", "contrast", "justify", "support", "challenge",
                "trend", "pattern", "development", "progress", "shift", "society", "economy", "politics", "culture", "globalization",
                "ethics", "responsibility", "accountability", "fairness", "equality", "technology", "innovation", "automation", "artificial", "digitalization",
                "environment", "sustainability", "climate", "resources", "consumption", "workplace", "leadership", "management", "strategy", "decision-making",
                "pressure", "stress", "burnout", "well-being", "motivation", "long-term", "short-term", "trade-off", "priority", "objective",
                "adapt", "adjust", "cope", "respond", "anticipate", "complex", "abstract", "practical", "theoretical", "systematic"
            ]
        
        # AKILLI FİLTRELEME (TEKRARI ÖNLER)
        learned_set = set(user_data.get("vocabulary_bank", []))
        unknown_words = [w for w in full_vocab_list if w not in learned_set]
        pool_to_select_from = unknown_words if len(unknown_words) >= 5 else full_vocab_list
        
        if pool_to_select_from:
            target_vocab = random.sample(pool_to_select_from, 5)

    st.session_state.lesson_active = True
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_seconds
    st.session_state.target_vocab = target_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    
    final_prompt = f"{system_role}\nCONTEXT: The student must try to use these words: {', '.join(target_vocab)}.\nIf they use one, PRAISE them briefly in parentheses."
    st.session_state.messages = [{"role": "system", "content": final_prompt}]
    
    try:
        first_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_msg = first_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        tts = gTTS(text=first_msg, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        st.session_state.last_audio_response = audio_fp.getvalue()
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")

# --- 4. ARAYÜZ ---
with st.sidebar:
    st.title("🎤 Pınar's Friend")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("API Key", type="password")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: st.metric("Seviye", user_data['current_level'])
    with c2: st.metric("Ders", user_data['lessons_completed'] + 1)
    
    st.info(f"📚 Kelime Hazinesi: {len(user_data['vocabulary_bank'])}")
    
    if st.session_state.get("lesson_active", False):
        st.divider()
        st.success(f"**Konu:** {st.session_state.topic}")
        if st.session_state.target_vocab:
            st.caption(f"**Hedefler:** {', '.join(st.session_state.target_vocab)}")
            
        current = st.session_state.accumulated_speaking_time
        target = st.session_state.target_speaking_seconds
        
        progress = min(current / target, 1.0)
        st.progress(progress, text=f"Konuşma Süren: {int(current)} / {int(target)} saniye")
        
        if current >= target:
            st.success("✅ Hedef Süre Doldu! Bitirebilirsin.")
        else:
            st.info(f"⏳ Daha {int(target - current)} saniye konuşmalısın.")

    st.divider()
    if st.button("RESET DATA"):
        save_data({"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT"})
        st.rerun()

# --- 5. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    st.title("🗣️ Active Speaking Coach")

    if not st.session_state.get("lesson_active", False):
        st.markdown(f"### Merhaba! Mod: **{user_data['next_mode']}**")
        st.markdown("*Sadece senin konuştuğun süre sayılır.*")
        
        target_sec = st.slider("Hedef Konuşma Süresi (Saniye)", 30, 300, 60, step=30)
        st.caption(f"Not: {target_sec} saniye net konuşma, yaklaşık {int(target_sec/0.6)} kelime demektir.")
        
        btn = "🚀 BAŞLAT" if user_data["next_mode"] != "EXAM" else "🔥 SINAV"
        
        if st.button(btn, type="primary", use_container_width=True):
            with st.spinner("Hazırlanıyor..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], target_sec)
                st.rerun()
    else:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
                    st.write(msg["content"])
        
        if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
            st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

        st.write("---")
        c_mic, c_fin = st.columns([1, 4])
        
        with c_mic:
            audio = mic_recorder(start_prompt="🎤 KONUŞ", stop_prompt="⏹️ GÖNDER", key="recorder")
        
        with c_fin:
            current_spk = st.session_state.accumulated_speaking_time
            target_spk = st.session_state.target_speaking_seconds
            
            if st.button("🏁 DERSİ BİTİR", use_container_width=True):
                if user_data["next_mode"] != "ASSESSMENT" and current_spk < target_spk:
                    st.toast("🚫 Yeterince konuşmadın!", icon="📢")
                    st.error(f"Daha çok konuşmalısın! Hedef: {int(target_spk)}sn, Sen: {int(current_spk)}sn")
                else:
                    st.session_state.lesson_active = False 
                    with st.spinner("Analiz Yapılıyor..."):
                        analysis_prompt = "ANALYZE session. OUTPUT ONLY JSON: {'score': 0-100, 'learned_words': [], 'level_recommendation': 'Stay/Up'}"
                        msgs = st.session_state.messages + [{"role": "system", "content": analysis_prompt}]
                        try:
                            res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                            rep = strict_json_parse(res.choices[0].message.content)
                            if not rep: rep = {"score": 80, "level_recommendation": "Stay"}

                            user_data["lessons_completed"] += 1
                            if "learned_words" in rep: 
                                user_data["vocabulary_bank"].extend(rep["learned_words"])
                            
                            if user_data["next_mode"] == "ASSESSMENT":
                                rec = rep.get("level_recommendation", "A2")
                                user_data["current_level"] = "B1" if "Up" in rec else "A2"
                                user_data["next_mode"] = "LESSON"
                                st.balloons()
                            elif user_data["lessons_completed"] % 5 == 0:
                                user_data["next_mode"] = "EXAM"
                            elif user_data["next_mode"] == "EXAM":
                                if rep.get("score", 0) >= 75:
                                    user_data["current_level"] = "B1" if user_data["current_level"]=="A2" else "B2"
                                    st.balloons()
                                user_data["next_mode"] = "LESSON"
                            else:
                                user_data["next_mode"] = "LESSON"
                                
                            save_data(user_data)
                            st.success("Kaydedildi!")
                            st.json(rep)
                        except Exception as e:
                            st.error(f"Analiz Hatası: {e}")
                        
                        if st.button("Ana Menü"): st.rerun()

        if audio:
            if "last_audio_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_audio_bytes:
                st.session_state.last_audio_bytes = audio['bytes']
                
                with st.spinner("İşleniyor..."):
                    try:
                        audio_bio = io.BytesIO(audio['bytes'])
                        audio_bio.name = "audio.webm"
                        
                        # --- 🔥 HALÜSİNASYON DÜZELTME (ANTI-HALLUCINATION) ---
                        # temperature=0: Yaratıcılığı sıfırla, sadece duyduğunu yaz
                        # prompt="...": Modelin boşlukta saçmalamasını engelle
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_bio, 
                            language="en",
                            temperature=0, 
                            prompt=f"The user is speaking English about {st.session_state.topic}. Do not make up words."
                        ).text
                        
                        # --- 🚨 FİLTRE: YASAKLI KELİMELERİ KONTROL ET ---
                        # Eğer Whisper saçmalamışsa (Hi how are you vb.), bunu YUT.
                        is_hallucination = False
                        for banned in ["Hi, how are you", "Thank you", "Copyright", "Amara.org", "Good to see you"]:
                            if banned.lower() in transcript.lower() and len(transcript) < 30:
                                is_hallucination = True
                                break
                        
                        if is_hallucination or not transcript.strip():
                            st.warning("Sesiniz tam alınamadı, lütfen tekrar konuşun.")
                        else:
                            # Her şey yolundaysa devam et
                            word_count = len(transcript.split())
                            estimated_seconds = word_count * 0.7 
                            st.session_state.accumulated_speaking_time += estimated_seconds
                            
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
