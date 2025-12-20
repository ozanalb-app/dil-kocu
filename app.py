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
import math
import pandas as pd
from datetime import datetime, timedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pınar's Friend v30.5 - Master Edition", page_icon="🧠", layout="wide")
DATA_FILE = "user_data.json"

# --- KELİME HAVUZU (HARDCODED) ---
STATIC_VOCAB_POOL = [
    "ask", "answer", "explain", "describe", "decide", "choose", "invite", "agree", "disagree", "believe", 
    "hope", "plan", "prepare", "practice", "improve", "change", "continue", "share", "miss", "travel", 
    "order", "pay", "save", "spend", "return", "borrow", "lend", "arrive", "leave", "follow", "stop", 
    "wait", "remember", "forget", "cancel", "delay", "confirm", "refuse", "accept", "suggest", "recommend", 
    "expect", "manage", "control", "avoid", "compare", "depend", "protect", "allow", "require", "solve", 
    "influence", "reduce", "increase", "develop", "organize", "arrange", "replace", "repair", "contact", 
    "complain", "request", "respond", "apologize", "promise", "warn", "encourage", "support", "handle", 
    "check", "review", "apply", "hire", "fire", "retire", "job", "work", "office", "company", "meeting", 
    "project", "task", "goal", "target", "problem", "solution", "idea", "opinion", "experience", "skill", 
    "responsibility", "duty", "role", "position", "contract", "agreement", "policy", "rule", "system", 
    "process", "result", "outcome", "reason", "cause", "effect", "decision", "choice", "option", "condition", 
    "situation", "opportunity", "risk", "advantage", "disadvantage", "progress", "success", "failure", 
    "mistake", "effort", "challenge", "chance", "future", "past", "present", "time", "schedule", "deadline", 
    "appointment", "period", "priority", "balance", "routine", "habit", "pressure", "stress", "price", 
    "cost", "value", "budget", "bill", "payment", "service", "quality", "reservation", "ticket", "trip", 
    "journey", "holiday", "transport", "destination", "route", "distance", "relationship", "trust", 
    "respect", "argument", "discussion", "conflict", "cooperation", "communication", "feedback", "important", 
    "different", "similar", "possible", "impossible", "common", "simple", "difficult", "clear", "unclear", 
    "serious", "normal", "special", "effective", "efficient", "successful", "unsuccessful", "early", "late", 
    "busy", "ready", "safe", "dangerous", "careful", "comfortable", "uncomfortable", "popular", "useful", 
    "useless", "suitable", "unsuitable", "familiar", "unfamiliar", "available", "unavailable", "necessary", 
    "unnecessary", "flexible", "responsible", "independent", "confident", "nervous", "satisfied", 
    "disappointed", "motivated", "bored", "focused", "society", "culture", "tradition", "organization", 
    "institution", "law", "regulation", "government", "authority", "public", "private", "community", 
    "population", "economy", "industry", "market", "competition", "technology", "internet", "information", 
    "data", "online", "digital", "platform", "software", "device", "network", "security", "privacy", 
    "media", "content", "resource", "access", "update"
]

# --- HALÜSİNASYON FİLTRESİ ---
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching",
    "Copyright", "Subscribe", "Amara.org", "Watch this video",
    "I could not think of anything", "Silence", "Bye", "MBC", "Al Jazeera",
    "Caption", "Subtitle"
]
_BANNED_PATTERNS = [re.compile(rf"\b{re.escape(p.lower())}\b") for p in BANNED_PHRASES]

# --- 2. SENARYO HAVUZU ---
SCENARIO_POOL = [
    "Parent teacher meeting",
    "Coffee Shop: Ordering a Latte with Oat Milk",
    "Hotel Reception: Checking in and Asking for Wi-Fi",
    "Street: Asking a Stranger for Directions to the Metro",
    "Restaurant: Asking for a Menu and Water",
    "Shop: Asking for the Price of a T-Shirt",
    "Pharmacy: Buying Aspirin for a Headache",
    "Taxi: Telling the Driver Where to Go",
    "Supermarket: Asking Where the Milk is",
    "Library: Registering for a Membership Card",
    "Cinema: Buying Two Tickets for a Comedy",
    "Clothing Store: Returning a Defective Shirt",
    "Restaurant: Complaining About Cold Food",
    "Train Station: Buying a Ticket and Asking for Platform",
    "Doctor's Office: Describing Symptoms (Fever/Cough)",
    "Hotel: Complaining About Noise from Next Door",
    "Airport Check-in: Requesting a Window Seat",
    "Job Interview: Answering 'Tell me about your experience'",
    "Bank: Opening a New Account",
    "Police Station: Reporting a Lost Wallet",
    "Tech Support: Internet Connection is Not Working",
    "Work: Negotiating a Deadline Extension with Boss",
    "Real Estate: Viewing an Apartment and Asking Details",
    "Car Rental: Negotiating Insurance Costs",
    "University: Asking a Professor for Feedback",
    "Insurance Company: Reporting a Car Accident",
    "Work: Resolving a Conflict with a Colleague",
    "Service: Canceling a Gym Membership (Hard Sell)",
    "Customs/Immigration: Explaining Purpose of Visit",
    "Event: Networking and Introducing Yourself",
    "Store: Haggle over the price of an antique"
]

# --- 3. YARDIMCI FONKSİYONLAR ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "current_level": "A2",
            "lessons_completed": 0,
            "vocab_srs": [], 
            "completed_scenarios": [],
            "lesson_history": [],
            "next_lesson_prep": None,
            "used_words": []
        }
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            if os.path.exists(DATA_FILE): os.rename(DATA_FILE, DATA_FILE + ".bak")
            return load_data()

        defaults = {
            "completed_scenarios": [],
            "vocab_srs": [],
            "next_lesson_prep": None,
            "lesson_history": [],
            "used_words": []
        }
        if "error_bank" in data: del data["error_bank"]
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def strict_json_parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except:
            return {}
    except:
        return {}

def determine_sub_level(level, lessons_completed):
    cycle = lessons_completed % 10
    if cycle < 3: return "Low"
    elif cycle < 7: return "Medium"
    else: return "High"

def generate_dynamic_vocab(client, scenario, level, user_data):
    used = set(user_data.get("used_words", []))
    available = [w for w in STATIC_VOCAB_POOL if w not in used]
    
    if len(available) < 10:
        available = STATIC_VOCAB_POOL
        user_data["used_words"] = [] 
    
    random.shuffle(available)
    candidates = available[:60]
    
    prompt = f"""
    Select exactly 5 English words from this list that are MOST relevant to the scenario: "{scenario}".
    CANDIDATES: {', '.join(candidates)}
    OUTPUT ONLY A JSON ARRAY of strings. Example: ["word1", "word2", "word3", "word4", "word5"]
    """
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        words = strict_json_parse(res.choices[0].message.content)
        if isinstance(words, list) and len(words) > 0:
            return words[:5]
        else:
            return candidates[:5]
    except:
        return candidates[:5]

# --- SRS MANTIĞI: SM-2 ALGORİTMASI ---
def calculate_sm2(quality, prev_interval, prev_ease_factor):
    new_ease_factor = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ease_factor < 1.3: new_ease_factor = 1.3

    if quality < 3: 
        new_interval = 0 
    else:
        if prev_interval == 0: new_interval = 1
        elif prev_interval == 1: new_interval = 6 if quality > 3 else 3
        else:
            new_interval = math.ceil(prev_interval * new_ease_factor)
            if quality == 3: new_interval = max(prev_interval + 1, math.floor(new_interval * 0.8))

    return new_interval, new_ease_factor

def get_next_srs_card(data, session_seen):
    now = time.time()
    srs_list = data.get("vocab_srs", [])
    
    due_cards = [
        card for card in srs_list 
        if card.get("next_review_ts", 0) <= now and card["word"] not in session_seen
    ]
    if due_cards:
        due_cards.sort(key=lambda x: x.get("next_review_ts", 0))
        return due_cards[0], "review"
    
    srs_words = {c["word"] for c in srs_list}
    new_candidates = [
        w for w in STATIC_VOCAB_POOL 
        if w not in srs_words and w not in session_seen
    ]
    if new_candidates:
        return {"word": random.choice(new_candidates)}, "new"
    
    return None, None

def update_srs_card_sm2(data, word_obj, quality):
    srs_list = data.get("vocab_srs", [])
    existing_idx = next((i for i, item in enumerate(srs_list) if item["word"] == word_obj["word"]), -1)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if existing_idx == -1:
        card = word_obj.copy()
        card["times_seen"] = 0
        card["interval"] = 0
        card["ease_factor"] = 2.5 
        card["history"] = []
    else:
        card = srs_list[existing_idx]
        if "ease_factor" not in card: card["ease_factor"] = 2.5
        if "interval" not in card: card["interval"] = 0

    prev_int = card.get("interval", 0)
    prev_ef = card.get("ease_factor", 2.5)
    new_int, new_ef = calculate_sm2(quality, prev_int, prev_ef)
    
    card["interval"] = new_int
    card["ease_factor"] = new_ef
    card["times_seen"] = card.get("times_seen", 0) + 1
    card["last_review"] = now_str
    
    next_ts = time.time() + (new_int * 24 * 60 * 60)
    if quality == 0: next_ts = time.time() + (10 * 60) 
        
    card["next_review_ts"] = next_ts
    if "history" not in card: card["history"] = []
    card["history"].append({"date": now_str, "quality": quality, "next_int": new_int})

    if existing_idx == -1: srs_list.append(card)
    else: srs_list[existing_idx] = card
        
    data["vocab_srs"] = srs_list
    save_data(data)

user_data = load_data()

# --- 4. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes, forced_scenario=None):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    # --- UPDATE: AKILLI SENARYO SEÇİMİ ---
    if forced_scenario:
        scenario = forced_scenario
    else:
        # Geçmişte yapılanları bul
        completed_scenarios = [h.get("topic") for h in user_data.get("lesson_history", [])]
        available_scenarios = [s for s in SCENARIO_POOL if s not in completed_scenarios]
        
        # Eğer hepsi bitmişse havuzu sıfırla
        if not available_scenarios:
            available_scenarios = SCENARIO_POOL
            
        scenario = random.choice(available_scenarios)
    # -------------------------------------

    target_vocab = generate_dynamic_vocab(client, scenario, level, user_data)
    
    for w in target_vocab:
        if w not in user_data["used_words"]:
            user_data["used_words"].append(w)
    save_data(user_data)

    if mode == "EXAM":
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. SCENARIO: {scenario}. CRITICAL: Ask concise questions. Do not give feedback."
    else:
        system_role = f"""
        ACT AS A ROLEPLAYER for: '{scenario}'. 
        LEVEL: {full_level_desc}.
        **INSTRUCTIONS:**
        1. FIRST MESSAGE: Ignore the scenario for a second. Start by warmly greeting Pınar and asking: "Hello Pınar, what did you do today?" (in English).
        2. WAIT for her answer about her day.
        3. AFTER she answers about her day: Acknowledge it briefly, then IMMEDIATELY TRANSITION into the roleplay scenario '{scenario}' as your character.
        **ROLEPLAY RULES (After transition):**
        - Keep responses SHORT (Max 25 words).
        - NEVER say "Good job".
        - MANDATORY: End every response with a relevant QUESTION about the scenario.
        """

    st.session_state.lesson_active = True
    st.session_state.current_mode = mode
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False
    st.session_state.final_report = None
    st.session_state.accumulated_speaking_time = 0.0
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60
    st.session_state.target_vocab = target_vocab
    st.session_state.scenario = scenario
    st.session_state.last_audio_bytes = None
    st.session_state.display_messages = []

    mode_icon = "📝 EXAM MODE" if mode == "EXAM" else "🎭 PRACTICE MODE"
    context_msg = f"{mode_icon}\n**SCENARIO:** {scenario}\n🔑 **WORDS:** {', '.join(target_vocab)}"
    st.session_state.display_messages.append({"role": "info", "content": context_msg})

    intro_prompt = f"{system_role}\nStart the conversation now with the greeting."
    st.session_state.messages = [{"role": "system", "content": intro_prompt}]

    try:
        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        msg = res.choices[0].message.content
        tr_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": f"Translate to Turkish: {msg}"}])
        tr_msg = tr_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.session_state.display_messages.append({"role": "assistant", "content": msg, "tr_content": tr_msg})
        tts = gTTS(text=msg, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.session_state.last_audio_response = fp.getvalue()
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")
        st.session_state.lesson_active = False

# --- 5. ARAYÜZ ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)

    with st.sidebar:
        st.title("🎓 Pınar's Academy")
        sub = determine_sub_level(user_data['current_level'], user_data['lessons_completed'])
        c1, c2 = st.columns(2)
        with c1: st.metric("Level", user_data['current_level'])
        with c2: st.metric("Band", sub)
        st.caption(f"Lessons Completed: {user_data['lessons_completed']}")

        st.divider()
        if st.button("📝 Take Level Exam", type="primary", use_container_width=True):
            start_lesson_logic(client, user_data["current_level"], "EXAM", 2.0)
            st.rerun()
        st.divider()
        
    page = st.sidebar.radio("📌 Menu", ["🎭 Scenario Coach", "👂 Listening Quiz", "🧠 Vocab Gym (Anki)", "📜 History & Stats"])

    # --- LISTENING QUIZ ---
    if page == "👂 Listening Quiz":
        st.title("👂 Listening & Dictation")
        if "quiz_text" not in st.session_state:
            st.session_state.quiz_text = None
            st.session_state.quiz_audio = None
            st.session_state.quiz_checked = False

        if st.button("🔊 New Audio"):
            with st.spinner("Generating..."):
                prompt = f"Generate a B1 level sentence. Just the sentence."
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                text = res.choices[0].message.content.strip().replace('"', '')
                st.session_state.quiz_text = text
                tts = gTTS(text=text, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.session_state.quiz_audio = fp.getvalue()
                st.session_state.quiz_checked = False
                st.rerun()

        if st.session_state.quiz_audio:
            st.audio(st.session_state.quiz_audio, format='audio/mp3')
            user_input = st.text_input("Type what you hear:")
            if st.button("Check"):
                st.session_state.quiz_checked = True

            if st.session_state.quiz_checked:
                clean_correct = re.sub(r'[^\w\s]', '', st.session_state.quiz_text).lower()
                clean_user = re.sub(r'[^\w\s]', '', user_input).lower()
                if clean_user == clean_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Correct: {st.session_state.quiz_text}")

    # --- VOCAB GYM (SRS ANKI STYLE) ---
    elif page == "🧠 Vocab Gym (Anki)":
        st.title("🧠 Vocabulary Gym (Anki SM-2)")

        if st.button("🚪 Quit / Reset", type="secondary", key="vocab_exit"):
            st.session_state.srs_active_card = None
            st.session_state.srs_revealed = False
            st.session_state.srs_audio = None
            st.rerun()

        if "srs_active_card" not in st.session_state:
            st.session_state.srs_active_card = None
            st.session_state.srs_revealed = False
            st.session_state.srs_audio = None
        if "gym_session_seen" not in st.session_state:
            st.session_state.gym_session_seen = set()

        if st.session_state.srs_active_card is None:
            card_data, card_type = get_next_srs_card(user_data, st.session_state.gym_session_seen)
            if card_data:
                if card_type == "new":
                    with st.spinner(f"Yeni kelime hazırlanıyor: {card_data['word']}..."):
                        word_choice = card_data['word']
                        prompt = f"""
                        Define the English word: "{word_choice}".
                        TARGET LEVEL: {user_data['current_level']}.
                        OUTPUT JSON ONLY:
                        {{
                            "word": "{word_choice}",
                            "tr": "TURKISH TRANSLATION HERE (MUST BE TURKISH)",
                            "ex": "Short English example sentence"
                        }}
                        """
                        try:
                            res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                            full_card = strict_json_parse(res.choices[0].message.content)
                            st.session_state.srs_active_card = full_card
                            st.session_state.srs_is_new = True
                            st.toast("✨ Yeni Kelime!")
                        except:
                            st.error("Bağlantı hatası.")
                else:
                    st.session_state.srs_active_card = card_data
                    st.session_state.srs_is_new = False
                    st.toast("↺ Tekrar Zamanı!")
                
                if st.session_state.srs_active_card:
                    st.session_state.gym_session_seen.add(st.session_state.srs_active_card["word"])
                    word = st.session_state.srs_active_card.get("word", "")
                    tts = gTTS(text=word, lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.session_state.srs_audio = fp.getvalue()
            else:
                st.info("🎉 Tebrikler! Şimdilik çalışılacak kelime kalmadı.")

        if st.session_state.srs_active_card:
            card = st.session_state.srs_active_card
            st.markdown(f"""
                <div style="border: 2px solid #4F8BF9; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px;">
                    <h1 style='color:#4F8BF9; font-size: 50px; margin:0;'>{card['word']}</h1>
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.srs_audio:
                st.audio(st.session_state.srs_audio, format='audio/mp3', autoplay=True)

            if not st.session_state.srs_revealed:
                if st.button("👀 Show Answer", use_container_width=True):
                    st.session_state.srs_revealed = True
                    st.rerun()
            else:
                st.success(f"🇹🇷 {card.get('tr', 'No Data')}")
                st.info(f"🇬🇧 {card.get('ex', 'No Data')}")
                
                if not st.session_state.srs_is_new:
                    ef = card.get('ease_factor', 2.5)
                    inter = card.get('interval', 0)
                    st.caption(f"📊 Stats: Ease: {ef:.2f} | Interval: {inter} days")

                st.markdown("### 🎛️ Rate Difficulty:")
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    if st.button("🟥 Again (0)", use_container_width=True):
                        update_srs_card_sm2(user_data, card, quality=0)
                        st.session_state.srs_active_card = None
                        st.session_state.srs_revealed = False
                        st.rerun()
                with c2:
                    if st.button("🟧 Hard (3)", use_container_width=True):
                        update_srs_card_sm2(user_data, card, quality=3)
                        st.session_state.srs_active_card = None
                        st.session_state.srs_revealed = False
                        st.rerun()
                with c3:
                    if st.button("🟩 Good (4)", use_container_width=True):
                        update_srs_card_sm2(user_data, card, quality=4)
                        st.session_state.srs_active_card = None
                        st.session_state.srs_revealed = False
                        st.rerun()
                with c4:
                    if st.button("🟦 Easy (5)", use_container_width=True):
                        update_srs_card_sm2(user_data, card, quality=5)
                        st.session_state.srs_active_card = None
                        st.session_state.srs_revealed = False
                        st.rerun()

    # --- HISTORY & STATS ---
    elif page == "📜 History & Stats":
        st.title("📜 Progress Log")
        st.subheader("📅 Daily Vocabulary Growth")
        
        hist_data = user_data.get("lesson_history", [])
        vocab_log = {}
        for h in hist_data:
            date_str = h.get("date", "Unknown")
            word_count = len(h.get("words", []))
            if date_str in vocab_log:
                vocab_log[date_str] += word_count
            else:
                vocab_log[date_str] = word_count
        
        if vocab_log:
            df_log = pd.DataFrame(list(vocab_log.items()), columns=["Date", "New Words Studied"])
            df_log = df_log.sort_values("Date", ascending=False)
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("Henüz veri yok.")

        st.divider()
        st.subheader("📚 Lesson History")
        if not hist_data: st.info("No history.")
        for h in reversed(hist_data):
            with st.expander(f"📚 {h.get('date')} - {h.get('topic')}"):
                st.write(f"**Score:** {h.get('score')}")
                br = h.get("breakdown", {})
                st.caption(f"Grammar: {br.get('grammar','-')} | Vocab: {br.get('vocabulary','-')} | Fluency: {br.get('fluency','-')}")
                st.success(f"**Artılar:** {', '.join(h.get('feedback_pros', []))}")
                st.error(f"**Eksiler:** {', '.join(h.get('feedback_cons', []))}")

    # --- SCENARIO COACH ---
    elif page == "🎭 Scenario Coach":
        st.title("🗣️ AI Roleplay Coach")

        if st.session_state.get("lesson_active", False) and not st.session_state.get("reading_phase", False):
            c_top1, c_top2 = st.columns([4, 1])
            with c_top1:
                st.info(f"🎙️ Speaking Phase | Target: {int(st.session_state.target_speaking_seconds // 60)} mins")
            with c_top2:
                if st.button("🚪 Quit / Reset", type="primary", use_container_width=True):
                    st.session_state.lesson_active = False
                    st.session_state.messages = []
                    st.session_state.reading_phase = False
                    st.session_state.scenario = None
                    st.rerun()

            with st.sidebar:
                curr = st.session_state.accumulated_speaking_time
                targ = st.session_state.target_speaking_seconds
                prog = min(curr / targ, 1.0) if targ > 0 else 0
                st.progress(prog, text=f"Time: {int(curr)}s / {int(targ)}s")

        if not st.session_state.get("lesson_active", False):
            # --- UPDATE: UI NEXT MISSION LOGIC ---
            if "temp_scenario" not in st.session_state or st.session_state.temp_scenario is None:
                if user_data.get("next_lesson_prep"):
                     st.session_state.temp_scenario = user_data["next_lesson_prep"].get("scenario")
                else:
                     completed_scenarios = [h.get("topic") for h in user_data.get("lesson_history", [])]
                     available_scenarios = [s for s in SCENARIO_POOL if s not in completed_scenarios]
                     
                     if not available_scenarios: available_scenarios = SCENARIO_POOL
                     st.session_state.temp_scenario = random.choice(available_scenarios)
            # -------------------------------------
            
            st.markdown(f"""
            <div style="padding:15px; background-color:#f0f2f6; border-radius:10px; margin-bottom:20px;">
                <h3>🎯 Next Mission: {st.session_state.temp_scenario}</h3>
                <p>Start chatting! First, tell me about your day (in English), then we'll dive into the scenario.</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔀 Change Scenario"):
                 st.session_state.temp_scenario = random.choice(SCENARIO_POOL)
                 st.rerun()

            mins = st.slider("Duration (Mins)", 0.5, 30.0, 1.0, step=0.5)
            
            if st.button("🚀 START SCENARIO"):
                forced = st.session_state.temp_scenario
                start_lesson_logic(client, user_data["current_level"], "LESSON", mins, forced_scenario=forced)
                st.session_state.temp_scenario = None 
                st.rerun()
        else:
            if not st.session_state.get("reading_phase", False):
                chat_cont = st.container()
                with chat_cont:
                    disp_msgs = st.session_state.get("display_messages", [])
                    for i, msg in enumerate(disp_msgs):
                        if msg["role"] == "info":
                            st.info(msg["content"])
                        elif msg["role"] == "user":
                            if "correction" in msg:
                                with st.expander("🛠️ Grammar Correction", expanded=True):
                                    st.markdown(f"**Doğrusu:** :green[{msg['correction']}]")
                            with st.chat_message("user", avatar="👤"):
                                st.write(msg["content"])
                        elif msg["role"] == "assistant":
                            is_last = (i == len(disp_msgs) - 1)
                            if is_last:
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.write("🔊 **Listening...**")
                                    with st.expander("🇬🇧 Text"):
                                        content = msg["content"]
                                        for w in st.session_state.target_vocab:
                                            content = re.sub(f"(?i)\\b{re.escape(w)}\\b", f"**:{'blue'}[{w.upper()}]**", content)
                                        st.markdown(content)
                                    with st.expander("🇹🇷 Türkçesi"):
                                        st.info(msg.get("tr_content", "..."))
                            else:
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.write(msg["content"])

                if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
                    st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

                st.write("---")
                c1, c2 = st.columns([1,4])
                with c1: audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️")
                with c2:
                    curr = st.session_state.accumulated_speaking_time
                    targ = st.session_state.target_speaking_seconds
                    time_up = (curr >= targ)
                    btn_text = "➡️ UNLOCK READING" if not time_up else "➡️ GO TO READING PHASE"
                    
                    if st.button(btn_text, use_container_width=True, disabled=not time_up):
                        st.session_state.reading_phase = True
                        with st.spinner("Generating reading task..."):
                            prompt = f"""
                            Create a short reading text (approx 150 words) specifically about this scenario: {st.session_state.scenario}. 
                            CRITICAL RULES:
                            1. The text MUST be consistent (e.g., if user complained about cold food, the text discusses cold food).
                            2. Generate 3 multiple-choice or open-ended questions based strictly on THIS text.
                            3. Do not ask questions about facts not present in the text.
                            
                            JSON Format: {{'text':'...','questions':['Q1','Q2','Q3']}}
                            """
                            try:
                                res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                                st.session_state.reading_content = strict_json_parse(res.choices[0].message.content)
                                if not st.session_state.reading_content: raise Exception("Empty JSON")
                            except:
                                st.session_state.reading_content = {"text": "Error loading text.", "questions": ["Q1", "Q2", "Q3"]}
                        st.rerun()

                if audio:
                    if "last_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_bytes:
                        st.session_state.last_bytes = audio['bytes']
                        if len(audio['bytes']) < 500:
                            st.warning("Audio unclear.")
                        else:
                            with st.spinner("Processing..."):
                                try:
                                    bio = io.BytesIO(audio['bytes'])
                                    bio.name = "audio.webm"
                                    
                                    # --- WHISPER DURATION FIX ---
                                    transcription = client.audio.transcriptions.create(
                                        model="whisper-1", 
                                        file=bio, 
                                        language="en", 
                                        temperature=0.2,
                                        response_format="verbose_json", 
                                        prompt=f"User speaking about scenario {st.session_state.scenario}."
                                    )
                                    txt = transcription.text
                                    st.session_state.accumulated_speaking_time += transcription.duration
                                    # ----------------------------

                                    txt_l = (txt or "").lower()
                                    bad = any(p.search(txt_l) for p in _BANNED_PATTERNS)

                                    if bad or len(txt.strip()) < 2:
                                        st.warning("Audio unclear.")
                                    else:
                                        # --- GRAMMAR CHECK FIX (CONTEXT AWARE) ---
                                        last_question = "Unknown context"
                                        for m in reversed(st.session_state.messages):
                                            if m["role"] == "assistant":
                                                last_question = m["content"]
                                                break
                                        
                                        corr = None
                                        try:
                                            p_check = f"""
                                            The user is answering this question: "{last_question}"
                                            The User said: '{txt}'
                                            TASK: Check grammar and logic.
                                            CRITICAL RULE FOR TENSES:
                                            - Analyze the QUESTION to determine the required tense.
                                            - If the question asks about the PAST (e.g., "What did you do?"), you MUST correct the user's sentence to PAST TENSE (e.g., "wake" -> "woke").
                                            - If the question is about routine/present, keep present tense.
                                            OTHER RULES:
                                            - IGNORE missing articles (a, an, the).
                                            - IGNORE capitalization.
                                            OUTPUT FORMAT:
                                            - If there is a tense mismatch with the question or a major error: return 'Correction: [Corrected Sentence]'.
                                            - If it is grammatically acceptable: return 'OK'.
                                            """
                                            c_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p_check}])
                                            ans = c_res.choices[0].message.content
                                            if "Correction:" in ans:
                                                corr = ans.replace("Correction:", "").strip()
                                        except: pass

                                        u_msg = {"role": "user", "content": txt}
                                        st.session_state.messages.append(u_msg)

                                        disp_u_msg = {"role": "user", "content": txt}
                                        if corr: disp_u_msg["correction"] = corr
                                        st.session_state.display_messages.append(disp_u_msg)

                                        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                                        rep = res.choices[0].message.content
                                        tr_rep = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":f"Translate to Turkish: {rep}"}]).choices[0].message.content

                                        st.session_state.messages.append({"role": "assistant", "content": rep})
                                        st.session_state.display_messages.append({"role": "assistant", "content": rep, "tr_content": tr_rep})

                                        tts = gTTS(text=rep, lang='en')
                                        fp = io.BytesIO()
                                        tts.write_to_fp(fp)
                                        st.session_state.last_audio_response = fp.getvalue()
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Audio Error: {e}")

            else:
                st.markdown("### 📖 Reading")
                if st.button("🚪 Quit / Reset", type="primary"):
                     st.session_state.lesson_active = False
                     st.session_state.reading_phase = False
                     st.session_state.reading_completed = False
                     st.session_state.messages = []
                     st.rerun()
                     
                if not st.session_state.get("reading_completed", False):
                    content = st.session_state.get("reading_content", {})
                    st.info(content.get("text", ""))

                    with st.form("read_form"):
                        ans_list = []
                        questions = content.get("questions", ["Q1", "Q2", "Q3"])
                        for i, q in enumerate(questions):
                            ans_list.append(st.text_input(f"{i+1}. {q}"))
                        submitted = st.form_submit_button("🏁 FINISH & GRADE")

                    if submitted:
                        with st.spinner("Detaylı Performans Analizi Yapılıyor (CEFR Standartları)..."):
                            r_text = st.session_state.reading_content.get("text", "")
                            r_qs = st.session_state.reading_content.get("questions", [])
                            target_words = st.session_state.target_vocab
                            
                            user_answers_with_context = []
                            for i, ans in enumerate(ans_list):
                                q_text = r_qs[i] if i < len(r_qs) else f"Question {i+1}"
                                user_answers_with_context.append({
                                    "question": q_text,
                                    "user_answer": ans
                                })

                            prompt = f"""
                            ACT AS A STRICT IELTS/CEFR EXAMINER. 
                            Analyze the User's performance based on the CHAT HISTORY and READING TASK.

                            --- DATA ---
                            TARGET VOCABULARY: {json.dumps(target_words)}
                            READING TEXT: "{r_text}"
                            READING ANSWERS: {json.dumps(user_answers_with_context)}
                            ------------

                            SCORING RUBRIC (Total 100 Points):
                            1. GRAMMAR & ACCURACY (0-20 pts): Correct verb tenses, prepositions, sentence structure.
                            2. VOCABULARY RANGE (0-20 pts): Variety of words AND usage of 'TARGET VOCABULARY'.
                            3. FLUENCY & RELEVANCE (0-20 pts): Did the user answer relevantly? Were sentences complete?
                            4. TASK ACHIEVEMENT (0-20 pts): Did they successfully complete the roleplay scenario goal?
                            5. READING COMPREHENSION (0-20 pts): Are the answers to reading questions correct based on the text?

                            OUTPUT JSON FORMAT (Strict):
                            {{
                                "scores": {{
                                    "grammar": 0,
                                    "vocabulary": 0,
                                    "fluency": 0,
                                    "task_achievement": 0,
                                    "reading": 0,
                                    "total_score": 0
                                }},
                                "used_target_words": ["word1", "word2"],
                                "reading_feedback": [
                                    {{
                                        "question": "...",
                                        "user_answer": "...",
                                        "correct_answer": "...",
                                        "is_correct": true/false
                                    }}
                                ],
                                "detailed_feedback": {{
                                    "grammar_review": "Turkish comment on grammar mistakes",
                                    "vocabulary_tips": "Turkish comment on better word choices",
                                    "general_pros": ["Tr Pro 1", "Tr Pro 2"],
                                    "general_cons": ["Tr Con 1", "Tr Con 2"]
                                }},
                                "next_lesson_homework": {{"scenario": "...", "vocab": ["..."]}}
                            }}
                            IMPORTANT: Provide 'pros' and 'cons' comments in TURKISH.
                            """
                            
                            msgs = st.session_state.messages + [{"role":"system","content":prompt}]

                            try:
                                res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                                rep = strict_json_parse(res.choices[0].message.content)
                                if not rep or "scores" not in rep:
                                     rep = {
                                         "scores": {"total_score": 0, "grammar": 0, "vocabulary": 0, "fluency": 0, "task_achievement": 0, "reading": 0},
                                         "detailed_feedback": {"general_pros": ["Hata oluştu"], "general_cons": ["Lütfen tekrar deneyin"]},
                                         "reading_feedback": []
                                     }

                                user_data["lessons_completed"] += 1
                                if "next_lesson_homework" in rep: 
                                    user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                                
                                hist = {
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "topic": st.session_state.scenario,
                                    "score": rep["scores"]["total_score"],
                                    "breakdown": rep["scores"],
                                    "words": st.session_state.target_vocab,
                                    "feedback_pros": rep["detailed_feedback"].get("general_pros", []),
                                    "feedback_cons": rep["detailed_feedback"].get("general_cons", [])
                                }
                                user_data["lesson_history"].append(hist)
                                save_data(user_data)

                                st.session_state.final_report = rep
                                st.session_state.reading_completed = True
                                st.rerun()
                            except Exception as e:
                                st.error(f"Analysis Error: {e}")

                else:
                    rep = st.session_state.final_report
                    st.balloons()
                    
                    total = rep["scores"]["total_score"]
                    st.markdown(f"<h1 style='text-align: center; color: #4F8BF9;'>🏆 Score: {total} / 100</h1>", unsafe_allow_html=True)

                    cols = st.columns(5)
                    cols[0].metric("Grammar", rep["scores"]["grammar"])
                    cols[1].metric("Vocab", rep["scores"]["vocabulary"])
                    cols[2].metric("Fluency", rep["scores"]["fluency"])
                    cols[3].metric("Task", rep["scores"]["task_achievement"])
                    cols[4].metric("Reading", rep["scores"]["reading"])

                    st.divider()

                    used_words = rep.get("used_target_words", [])
                    all_targets = st.session_state.target_vocab
                    st.write("### 🎯 Target Words Check")
                    
                    if all_targets:
                        word_cols = st.columns(len(all_targets))
                        for i, word in enumerate(all_targets):
                            if word in used_words:
                                word_cols[i].success(f"✅ {word}")
                            else:
                                word_cols[i].error(f"❌ {word}")

                    st.divider()

                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("👍 İyi Yönler")
                        for item in rep["detailed_feedback"].get("general_pros", []):
                            st.success(f"• {item}")
                        
                        st.info(f"**💡 Vocab Tips:** {rep['detailed_feedback'].get('vocabulary_tips', '')}")

                    with c2:
                        st.subheader("👎 Gelişmeli")
                        for item in rep["detailed_feedback"].get("general_cons", []):
                            st.error(f"• {item}")

                        st.warning(f"**🛠️ Grammar:** {rep['detailed_feedback'].get('grammar_review', '')}")

                    st.write("---")
                    with st.expander("📖 Reading Quiz Details"):
                        for fb in rep.get("reading_feedback", []):
                            color = "green" if fb["is_correct"] else "red"
                            st.markdown(f"**Soru:** {fb['question']}")
                            st.write(f"Siz: {fb['user_answer']}")
                            st.markdown(f":{color}[Doğru Cevap: {fb['correct_answer']}]")
                            st.divider()
                    
                    with st.expander("🔧 Debug: Raw Analysis Data"):
                        st.json(rep)

                    if st.button("🚀 START NEXT LESSON (Hard Reset)", type="primary", use_container_width=True):
                        st.session_state.lesson_active = False
                        st.session_state.messages = []
                        st.session_state.display_messages = []
                        st.session_state.reading_phase = False
                        st.session_state.reading_completed = False
                        st.session_state.final_report = None
                        st.session_state.accumulated_speaking_time = 0.0
                        st.session_state.scenario = None
                        st.session_state.temp_scenario = None
                        st.rerun()
else:
    st.warning("Enter API Key")
