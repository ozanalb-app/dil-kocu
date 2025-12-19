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
from datetime import datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pınar's Friend v28 (Final)", page_icon="🛡️", layout="wide")
DATA_FILE = "user_data.json"

# --- HALÜSİNASYON FİLTRESİ (CASE-INSENSITIVE) ---
HALLUCINATION_TRIGGERS = [
    "thank you for watching", "copyright", "subscribe", "amara.org", 
    "silence", "mbc", "al jazeera", "caption", "subtitle"
]

SCENARIO_POOL = [
    "Coffee Shop: Ordering a Latte with Oat Milk",
    "Hotel Reception: Checking in and Asking for Wi-Fi",
    "Job Interview: Answering 'Tell me about yourself'",
    "Doctor's Appointment: Describing Symptoms",
    "Restaurant: Complaining About Cold Food",
    "Airport: Requesting a Window Seat",
    "Tech Support: Internet Connection Issues",
    "Real Estate: Viewing an Apartment",
    "Pharmacy: Asking for painkillers",
    "Supermarket: Asking for organic vegetables",
    "Gym: Asking about membership fees",
    "Bank: Reporting a lost card"
]

# --- 2. DATA YÖNETİMİ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "current_level": "A2", "lessons_completed": 0, 
            "completed_scenarios": [], "lesson_history": [], 
            "error_bank": [], "next_lesson_prep": None
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        # Eksik key kontrolü
        defaults = {
            "completed_scenarios": [], "error_bank": [], "next_lesson_prep": None,
            "lesson_history": []
        }
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def determine_sub_level(level, lessons_completed):
    cycle = lessons_completed % 10
    if cycle < 3: return "Low"
    elif cycle < 7: return "Medium"
    else: return "High"

# --- 3. AI MOTORU (GÜVENLİ & JSON GARANTİLİ) ---

def get_ai_response_json(client, messages, model="gpt-4o"):
    """
    Tek çağrıda JSON çıktısı alır. Hata olursa None döner.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"}, # JSON Modu
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Connection Error: {e}")
        return None

def generate_dynamic_vocab(client, scenario, level):
    # Çift tırnaklı, valid JSON prompt
    prompt = f"""
    Generate 5 English vocabulary words suitable for CEFR level {level}.
    Target Scenario: "{scenario}".
    Return JSON: {{ "words": ["word1", "word2", "word3", "word4", "word5"] }}
    """
    res = get_ai_response_json(client, [{"role": "user", "content": prompt}])
    return res.get("words", ["hello", "speak", "learn"]) if res else ["hello", "speak"]

def start_lesson_logic(client, user_data, mode, duration, forced_scenario=None):
    """
    Ders başlatma ve state sıfırlama.
    """
    level = user_data["current_level"]
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level = f"{level} ({sub_level})"
    
    # 1. Senaryo Seçimi
    scenario = "General Chat"
    if forced_scenario:
        scenario = forced_scenario
    elif mode == "EXAM":
        scenario = random.choice(SCENARIO_POOL)
    else: # LESSON
        if user_data.get("next_lesson_prep"):
            prep = user_data["next_lesson_prep"]
            scenario = prep.get("scenario", prep.get("topic", "General"))
            user_data["next_lesson_prep"] = None # Tüket
            save_data(user_data)
        else:
            completed = user_data.get("completed_scenarios", [])
            available = [s for s in SCENARIO_POOL if s not in completed]
            if not available:
                user_data["completed_scenarios"] = [] # Sıfırla
                save_data(user_data)
                available = SCENARIO_POOL
            
            scenario = random.choice(available)
            if scenario not in user_data["completed_scenarios"]:
                user_data["completed_scenarios"].append(scenario)
                save_data(user_data)

    # 2. Kelime Seçimi
    target_vocab = generate_dynamic_vocab(client, scenario, level)

    # 3. System Prompt (JSON Structure)
    system_prompt = f"""
    ACT AS A ROLEPLAYER for: '{scenario}'. Level: {full_level}.
    
    IMPORTANT: You must ALWAYS reply in VALID JSON format.
    Structure:
    {{
        "english_response": "Your reply in English (Max 25 words). End with a question.",
        "turkish_translation": "The Turkish translation.",
        "correction": null
    }}
    
    If the user makes a MAJOR mistake, set "correction" to "User said: [X], Correct: [Y]". 
    Otherwise set "correction" to null (the literal null, not a string).
    
    Start the roleplay now with your first line.
    """

    # 4. State Hard Reset
    st.session_state.lesson_active = True
    st.session_state.current_mode = mode
    st.session_state.scenario = scenario
    st.session_state.target_vocab = target_vocab
    st.session_state.target_seconds = duration * 60
    
    # 🔥 BUG FIX: İsim birliği sağlandı
    st.session_state.accumulated_speaking_time = 0.0
    
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False
    st.session_state.final_report = None
    
    # 5. İlk Mesajı Al
    first_response = get_ai_response_json(client, st.session_state.messages)
    if first_response:
        st.session_state.messages.append({"role": "assistant", "content": json.dumps(first_response)})
        
        # Sesi hazırla
        try:
            tts = gTTS(text=first_response["english_response"], lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.session_state.last_audio = fp.getvalue()
        except:
            st.session_state.last_audio = None

# --- 4. UYGULAMA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)
    user_data = load_data()

    # --- SIDEBAR (Global) ---
    with st.sidebar:
        st.title("🎓 Pınar's Academy")
        c1, c2 = st.columns(2)
        with c1: st.metric("Level", user_data['current_level'])
        with c2: st.metric("Done", user_data['lessons_completed'])
        
        if user_data.get("error_bank"):
            st.divider()
            st.caption("🚨 Recent Errors")
            # Son 3 hatayı göster (Ters sıra)
            for err in list(reversed(user_data["error_bank"]))[:3]:
                st.error(f"{err.get('note', 'Error')}")
            
            if st.button("Clear Errors"):
                user_data["error_bank"] = []
                save_data(user_data)
                st.rerun()

    # --- SAYFA SEÇİMİ ---
    if not st.session_state.get("lesson_active", False):
        st.title("🎭 Scenario Coach")
        
        # Gelecek Dersi Göster
        next_sc = "Surprise Scenario"
        if user_data.get("next_lesson_prep"):
            prep = user_data["next_lesson_prep"]
            next_sc = prep.get("scenario", prep.get("topic", "Unknown"))
        
        st.info(f"📍 **Next Up:** {next_sc}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔀 Shuffle Scenario"):
                new_sc = random.choice(SCENARIO_POOL)
                st.session_state.temp_sc = new_sc
                st.toast(f"Switched to: {new_sc}")
                st.rerun()
        
        with col2:
            mins = st.slider("Target (Mins)", 0.5, 10.0, 1.0, step=0.5)
        
        if st.button("🚀 START LESSON", type="primary", use_container_width=True):
            forced = st.session_state.get("temp_sc")
            start_lesson_logic(client, user_data, "LESSON", mins, forced_scenario=forced)
            st.session_state.temp_sc = None
            st.rerun()

    else:
        # --- AKTİF DERS EKRANI ---
        st.subheader(f"🎭 {st.session_state.scenario}")
        
        # Reading'e Geçiş Kontrolü
        if not st.session_state.get("reading_phase", False):
            # Kelimeleri Göster
            st.caption(f"🔑 Use these words: {', '.join(st.session_state.target_vocab)}")
            
            # --- CHAT ARAYÜZÜ (FIX: Height Kaldırıldı) ---
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.messages:
                    if msg["role"] == "system": continue
                    
                    if msg["role"] == "user":
                        with st.chat_message("user", avatar="👤"):
                            st.write(msg["content"])
                    
                    elif msg["role"] == "assistant":
                        # JSON içeriğini parse et (Safe)
                        try:
                            data = json.loads(msg["content"])
                            with st.chat_message("assistant", avatar="🤖"):
                                # Hata Düzeltmesi (Varsa)
                                if data.get("correction"):
                                    st.error(f"🛠️ {data['correction']}")
                                
                                # İngilizce Mesaj
                                txt = data.get("english_response", "")
                                # Kelime vurgusu (Blue)
                                for w in st.session_state.target_vocab:
                                    txt = re.sub(f"(?i)\\b{re.escape(w)}\\b", f"**:{'blue'}[{w.upper()}]**", txt)
                                st.markdown(txt)
                                
                                # Türkçe Çeviri
                                with st.expander("🇹🇷 Translation"):
                                    st.caption(data.get("turkish_translation", ""))
                        except:
                            st.error("Display Error")

            # --- SES PLAYER ---
            if st.session_state.get("last_audio"):
                st.audio(st.session_state.last_audio, format="audio/mp3", autoplay=True)

            st.divider()

            # --- KONTROL PANELİ ---
            col_mic, col_prog, col_btn = st.columns([1, 2, 1])
            
            with col_mic:
                audio = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹️ Stop", key="recorder")
            
            with col_prog:
                # 🔥 FIX: Değişken adı düzeltildi
                curr = st.session_state.accumulated_speaking_time
                targ = st.session_state.target_seconds
                prog = min(curr / targ, 1.0) if targ > 0 else 0
                st.progress(prog, text=f"{int(curr)}s / {int(targ)}s")
            
            with col_btn:
                can_pass = (curr >= targ) or st.session_state.current_mode == "EXAM"
                btn_label = "➡️ Reading" if can_pass else "🔒 Locked"
                
                if st.button(btn_label, disabled=not can_pass, use_container_width=True):
                    st.session_state.reading_phase = True
                    # Reading oluştur
                    with st.spinner("Preparing text..."):
                        p = f"""
                        Create A2/B1 reading about '{st.session_state.scenario}'. 
                        Return JSON: {{"text":"...", "questions":["Q1","Q2","Q3"]}}
                        """
                        res = get_ai_response_json(client, [{"role":"user", "content":p}])
                        st.session_state.reading_content = res or {"text": "Error", "questions": ["Error"]}
                    st.rerun()

            # --- SES İŞLEME ---
            if audio:
                if "last_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_bytes:
                    st.session_state.last_bytes = audio['bytes']
                    
                    if len(audio['bytes']) < 500:
                        st.toast("⚠️ Audio too short!", icon="❌")
                    else:
                        with st.spinner("Thinking..."):
                            # 1. Transcribe
                            bio = io.BytesIO(audio['bytes'])
                            bio.name = "audio.webm"
                            try:
                                transcript = client.audio.transcriptions.create(
                                    model="whisper-1", file=bio, language="en"
                                ).text
                            except:
                                transcript = ""
                            
                            # 2. Filtre (Case-Insensitive)
                            t_lower = transcript.lower()
                            is_bad = any(b in t_lower for b in HALLUCINATION_TRIGGERS)
                            
                            if is_bad or len(transcript.strip()) < 2:
                                st.toast("⚠️ Unclear audio", icon="🙉")
                            else:
                                # 3. Zaman Ekle (Basit kelime bazlı)
                                st.session_state.accumulated_speaking_time += len(transcript.split()) * 0.8
                                
                                # 4. Mesaj Ekle ve Gönder
                                st.session_state.messages.append({"role": "user", "content": transcript})
                                
                                # 5. AI Yanıtı Al (JSON)
                                ai_response = get_ai_response_json(client, st.session_state.messages)
                                
                                if ai_response:
                                    # Cevabı kaydet
                                    st.session_state.messages.append({"role": "assistant", "content": json.dumps(ai_response)})
                                    
                                    # Hata varsa bankaya at
                                    if ai_response.get("correction"):
                                        user_data["error_bank"].append({"date": str(datetime.now()), "note": ai_response["correction"]})
                                        save_data(user_data)
                                    
                                    # Sesi hazırla
                                    try:
                                        tts = gTTS(text=ai_response["english_response"], lang='en')
                                        fp = io.BytesIO()
                                        tts.write_to_fp(fp)
                                        st.session_state.last_audio = fp.getvalue()
                                    except: pass
                                    
                                    st.rerun()

        # --- READING PHASE ---
        else:
            st.markdown("### 📖 Reading Comprehension")
            content = st.session_state.get("reading_content", {})
            st.info(content.get("text", "No text generated."))
            
            with st.form("reading_form"):
                answers = []
                for q in content.get("questions", ["Q1", "Q2", "Q3"]):
                    answers.append(st.text_input(q))
                
                if st.form_submit_button("🏁 Finish Lesson"):
                    with st.spinner("Grading..."):
                        # Analiz İste (Token optimizasyonu: Sadece son 6 mesajı gönder)
                        recent_history = st.session_state.messages[-6:]
                        
                        p_anal = """
                        Analyze the session. Return JSON:
                        {
                            "score": 0-100,
                            "pros": ["point1", "point2"],
                            "cons": ["point1", "point2"],
                            "next_homework": {"scenario": "New Scenario", "vocab": ["word1"]}
                        }
                        """
                        # Kullanıcı cevaplarını JSON string yapıp gönder
                        q_json = json.dumps(answers)
                        
                        msgs = [{"role":"system", "content": p_anal}, 
                                {"role":"user", "content": f"Session Partial History: {str(recent_history)}. Reading Answers: {q_json}"}]
                        
                        res = get_ai_response_json(client, msgs)
                        
                        if res:
                            # Kaydet
                            user_data["lessons_completed"] += 1
                            user_data["next_lesson_prep"] = res.get("next_homework")
                            
                            h_entry = {
                                "date": str(datetime.now().strftime("%Y-%m-%d")),
                                "scenario": st.session_state.scenario,
                                "score": res.get("score"),
                                "pros": res.get("pros"),
                                "cons": res.get("cons")
                            }
                            user_data["lesson_history"].append(h_entry)
                            save_data(user_data)
                            
                            st.session_state.final_report = res
                            st.session_state.reading_completed = True
                            st.rerun()

            # Rapor Ekranı
            if st.session_state.get("reading_completed"):
                rep = st.session_state.final_report
                st.balloons()
                st.success(f"Score: {rep.get('score', 0)}")
                
                c1, c2 = st.columns(2)
                with c1: st.write("✅ **Pros**", rep.get('pros', []))
                with c2: st.write("🔻 **Cons**", rep.get('cons', []))
                
                next_hw = rep.get('next_homework', {})
                st.info(f"Next Mission: {next_hw.get('scenario', 'Unknown')}")
                
                if st.button("Start Next Lesson (Reset)"):
                    st.session_state.lesson_active = False
                    st.session_state.reading_phase = False
                    st.session_state.reading_completed = False
                    st.session_state.final_report = None
                    st.session_state.accumulated_speaking_time = 0
                    st.rerun()

else:
    st.warning("Please enter your OpenAI API Key in the sidebar.")
