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
import base64  # <--- YENİ EKLENDİ
import pandas as pd
from datetime import datetime, timedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pınar's Friend v37 - iOS Master", page_icon="🧠", layout="wide")
DATA_FILE = "user_data.json"

# --- KELİME HAVUZU ---
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

# --- SENARYO HAVUZU ---
SCENARIO_POOL = [
    "Parent teacher meeting", "Coffee Shop: Ordering a Latte", "Hotel Reception: Checking in",
    "Street: Asking for Directions", "Restaurant: Ordering Food", "Shop: Buying Clothes",
    "Pharmacy: Buying Medicine", "Taxi: Giving Directions", "Supermarket: Shopping",
    "Job Interview", "Bank: Opening Account", "Doctor: Describing Symptoms"
]

# --- YEDEK SINAV VERİSİ ---
BACKUP_EXAM_DATA = {
    "VOCABULARY": [
        {"question": "A place where you can borrow books without buying them.", "options": ["Library", "Bookstore", "Pharmacy", "Bank"], "answer": "Library"},
        {"question": "To come to a place after traveling.", "options": ["Arrive", "Leave", "Stay", "Live"], "answer": "Arrive"},
        {"question": "A person who works in a hospital and helps doctors.", "options": ["Nurse", "Engineer", "Teacher", "Driver"], "answer": "Nurse"},
    ] * 5,
    "GRAMMAR": [
        {"sentence": "She ____ (go) to the cinema yesterday.", "answer": "went"},
        {"sentence": "I have never ____ (see) that movie.", "answer": "seen"},
        {"sentence": "If it rains, we ____ (stay) at home.", "answer": "will stay"},
    ] * 5,
    "READING": {
        "text": """
        Sarah loves weekends. On Saturdays, she usually wakes up at 9 AM and has a big breakfast with her family. They eat eggs, toast, and drink orange juice. After breakfast, Sarah goes to the park to play tennis with her friends. She has been playing tennis for five years and is very good at it. 
        
        This Saturday was different, however. It rained heavily all day, so Sarah could not go to the park. Instead, she decided to stay home and read a book. Her brother, Tom, played video games in the living room. Their mother baked a chocolate cake, which made the whole house smell delicious. Although she couldn't play tennis, Sarah enjoyed her relaxing day indoors. She realized that sometimes doing nothing is the best way to rest.
        """,
        "questions": [
            {"question": "What does Sarah usually do on Saturday mornings?", "options": ["Goes to school", "Plays tennis", "Has a big breakfast", "Sleeps until noon"], "answer": "Has a big breakfast"},
            {"question": "Why didn't Sarah go to the park this Saturday?", "options": ["She was sick", "It was raining", "Her friends were busy", "She wanted to read"], "answer": "It was raining"},
            {"question": "How long has Sarah been playing tennis?", "options": ["Five years", "Two years", "Since last year", "Ten years"], "answer": "Five years"},
            {"question": "What did Sarah's mother do?", "options": ["Played video games", "Went to work", "Baked a cake", "Read a book"], "answer": "Baked a cake"},
            {"question": "How did Sarah feel about her day in the end?", "options": ["Bored", "Angry", "Sad", "Relaxed"], "answer": "Relaxed"}
        ]
    },
    "SPEAKING_TOPIC": "Describe your favorite way to spend a rainy day."
}

# --- YARDIMCI FONKSİYONLAR ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"current_level": "A2", "lessons_completed": 0, "vocab_srs": [], "completed_scenarios": [], "lesson_history": [], "next_lesson_prep": None, "used_words": []}
    with open(DATA_FILE, "r") as f:
        try: return json.load(f)
        except: return load_data()

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

def strict_json_parse(text):
    text = text.strip()
    if text.startswith("```"): text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    try: return json.loads(text)
    except:
        try: 
            s = text.find("{"); e = text.rfind("}") + 1
            return json.loads(text[s:e])
        except: return {}

def determine_sub_level(level, lessons_completed):
    cycle = lessons_completed % 10
    if cycle < 3: return "Low"
    elif cycle < 7: return "Mid"
    else: return "High"

# --- YENİ EKLENEN: iPHONE UYUMLU SES OYNATICI ---
def autoplay_audio(audio_bytes):
    """
    iPhone/Safari ve Android uyumlu HTML5 Base64 Ses Oynatıcı.
    """
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio controls autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        Your browser does not support the audio element.
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)
# ------------------------------------------------

def generate_dynamic_vocab(client, scenario, level, user_data):
    used = set(user_data.get("used_words", []))
    available = [w for w in STATIC_VOCAB_POOL if w not in used]
    if len(available) < 10: available = STATIC_VOCAB_POOL
    random.shuffle(available)
    candidates = available[:60]
    prompt = f"Select 5 relevant words for '{scenario}' from: {', '.join(candidates)}. JSON Array output."
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return strict_json_parse(res.choices[0].message.content)[:5]
    except: return candidates[:5]

def generate_exam_questions(client, level):
    prompt = f"""
    Create a comprehensive {level} level English exam JSON structure with 4 PARTS.
    KEYS MUST BE: "VOCABULARY", "GRAMMAR", "READING", "SPEAKING_TOPIC".
    
    1. VOCABULARY: 15 multiple-choice questions. 
       Format: {{"question": "Long definition sentence...", "options": ["Word A", "Word B", "Word C", "Word D"], "answer": "Word A"}}
       
    2. GRAMMAR: 15 fill-in-the-blank questions. 
       Format: {{"sentence": "She ____ (go) yesterday.", "answer": "went"}}
       
    3. READING: 
       - A text paragraph (Minimum 10 sentences, approx 150 words).
       - 5 Multiple choice questions based on the text.
       Format: {{
           "text": "Full text here...",
           "questions": [
               {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}}
           ]
       }}
       
    4. SPEAKING_TOPIC: String (e.g. "Talk about your hobbies").
    
    OUTPUT RAW JSON ONLY.
    """
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":prompt}])
        data = strict_json_parse(res.choices[0].message.content)
        normalized = {}
        for k, v in data.items(): normalized[k.upper()] = v
        if "READING" not in normalized or "questions" not in normalized["READING"]:
            return BACKUP_EXAM_DATA 
        return normalized
    except:
        return BACKUP_EXAM_DATA

# --- SRS VE SM-2 ---
def calculate_sm2(quality, prev_interval, prev_ease_factor):
    new_ef = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ef < 1.3: new_ef = 1.3
    if quality < 3: new_int = 0
    else:
        if prev_interval == 0: new_int = 1
        elif prev_interval == 1: new_int = 6 if quality > 3 else 3
        else: new_int = math.ceil(prev_interval * new_ef)
    return new_int, new_ef

def get_next_srs_card(data, session_seen):
    now = time.time()
    srs_list = data.get("vocab_srs", [])
    due = [c for c in srs_list if c.get("next_review_ts", 0) <= now and c["word"] not in session_seen]
    if due: 
        due.sort(key=lambda x: x.get("next_review_ts", 0))
        return due[0], "review"
    srs_words = {c["word"] for c in srs_list}
    new_cands = [w for w in STATIC_VOCAB_POOL if w not in srs_words and w not in session_seen]
    if new_cands: return {"word": random.choice(new_cands)}, "new"
    return None, None

def update_srs_card_sm2(data, word_obj, quality):
    srs_list = data.get("vocab_srs", [])
    idx = next((i for i, item in enumerate(srs_list) if item["word"] == word_obj["word"]), -1)
    if idx == -1:
        card = word_obj.copy(); card.update({"times_seen":0, "interval":0, "ease_factor":2.5, "history":[]})
    else: card = srs_list[idx]
    n_int, n_ef = calculate_sm2(quality, card.get("interval",0), card.get("ease_factor",2.5))
    card.update({"interval": n_int, "ease_factor": n_ef, "times_seen": card.get("times_seen",0)+1})
    card["next_review_ts"] = time.time() + (n_int * 86400)
    if quality == 0: card["next_review_ts"] = time.time() + 600
    if idx == -1: srs_list.append(card)
    else: srs_list[idx] = card
    data["vocab_srs"] = srs_list
    save_data(data)

user_data = load_data()

# --- DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes, forced_scenario=None):
    sub = determine_sub_level(level, user_data["lessons_completed"])
    if forced_scenario: sc = forced_scenario
    else:
        done = [h.get("topic") for h in user_data.get("lesson_history", [])]
        avail = [s for s in SCENARIO_POOL if s not in done]
        sc = random.choice(avail if avail else SCENARIO_POOL)

    vocab = generate_dynamic_vocab(client, sc, level, user_data)
    st.session_state.lesson_active = True
    st.session_state.current_mode = mode
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False
    st.session_state.final_report = None
    st.session_state.accumulated_speaking_time = 0.0
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60
    st.session_state.target_vocab = vocab
    st.session_state.scenario = sc
    st.session_state.messages = [{"role": "system", "content": f"ACT AS ROLEPLAYER: {sc}. Level: {level}. Ask 'Hello Pınar, what did you do today?' first."}]
    
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        msg = res.choices[0].message.content
        tr_msg = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"Translate: {msg}"}]).choices[0].message.content
        st.session_state.display_messages = [{"role":"assistant", "content":msg, "tr_content":tr_msg}]
        st.session_state.messages.append({"role":"assistant", "content":msg})
        
        tts = gTTS(text=msg, lang='en')
        fp = io.BytesIO(); tts.write_to_fp(fp)
        st.session_state.last_audio_response = fp.getvalue()
    except: st.error("Start Error")

# --- ARAYÜZ ---
if "OPENAI_API_KEY" in st.secrets: api_key = st.secrets["OPENAI_API_KEY"]
else: 
    with st.sidebar: api_key = st.text_input("API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)
    
    with st.sidebar:
        st.title("🎓 Pınar's Academy")
        c1, c2 = st.columns(2)
        c1.metric("Level", user_data['current_level'])
        c2.metric("Lessons", user_data['lessons_completed'])
        
        st.divider()
        if st.button("📝 Take Level Exam", type="primary", use_container_width=True):
            st.session_state.exam_active = True
            st.session_state.lesson_active = False
            st.session_state.exam_data = None
            st.rerun()
        st.divider()

    # --- SINAV MODU ---
    if st.session_state.get("exam_active", False):
        st.title("📝 Level Assessment Exam")
        
        if "exam_data" not in st.session_state or st.session_state.exam_data is None:
            with st.spinner("Preparing Exam (Vocab, Grammar, Reading, Speaking)..."):
                data = generate_exam_questions(client, user_data['current_level'])
                st.session_state.exam_data = data
                st.session_state.exam_answers = {}
                st.session_state.exam_step = 1
                st.rerun()
        
        data = st.session_state.exam_data
        
        # 1. VOCAB
        if st.session_state.exam_step == 1:
            st.subheader("Part 1: Vocabulary")
            st.progress(25)
            with st.form("exam_v"):
                for i, q in enumerate(data["VOCABULARY"][:15]):
                    st.write(f"**{i+1}.** {q['question']}")
                    st.session_state.exam_answers[f"v_{i}"] = st.radio(f"Opt {i}", q['options'], key=f"vr_{i}", label_visibility="collapsed")
                    st.write("---")
                if st.form_submit_button("Next ➡️"): 
                    st.session_state.exam_step = 2
                    st.rerun()

        # 2. GRAMMAR
        elif st.session_state.exam_step == 2:
            st.subheader("Part 2: Grammar")
            st.progress(50)
            with st.form("exam_g"):
                for i, q in enumerate(data["GRAMMAR"][:15]):
                    st.write(f"**{i+1}.** {q['sentence']}")
                    st.session_state.exam_answers[f"g_{i}"] = st.text_input("Answer", key=f"gi_{i}", label_visibility="collapsed")
                    st.write("---")
                if st.form_submit_button("Next ➡️"): 
                    st.session_state.exam_step = 3
                    st.rerun()

        # 3. READING
        elif st.session_state.exam_step == 3:
            st.subheader("Part 3: Reading Comprehension")
            st.progress(75)
            r_data = data.get("READING", {})
            st.info(r_data.get("text", "Text unavailable."))
            with st.form("exam_r"):
                for i, q in enumerate(r_data.get("questions", [])[:5]):
                    st.write(f"**{i+1}.** {q['question']}")
                    st.session_state.exam_answers[f"r_{i}"] = st.radio(f"Opt {i}", q['options'], key=f"rr_{i}", label_visibility="collapsed")
                    st.write("---")
                if st.form_submit_button("Next ➡️"): 
                    st.session_state.exam_step = 4
                    st.rerun()

        # 4. SPEAKING
        elif st.session_state.exam_step == 4:
            st.subheader("Part 4: Speaking")
            st.progress(90)
            topic = data.get("SPEAKING_TOPIC", "Describe your day.")
            if isinstance(topic, list): topic = topic[0]
            st.info(f"🎙️ **Topic:** {topic}")
            st.warning("⚠️ Speak for at least 15 seconds.")
            audio = mic_recorder(start_prompt="🎤 Record", stop_prompt="⏹️ Stop")
            if audio:
                with st.spinner("Analyzing..."):
                    bio = io.BytesIO(audio['bytes']); bio.name = "ex.webm"
                    try:
                        res = client.audio.transcriptions.create(model="whisper-1", file=bio, response_format="verbose_json")
                        if res.duration < 15:
                            st.error(f"Too short ({res.duration:.1f}s). Try again.")
                        else:
                            st.session_state.exam_answers["speaking_text"] = res.text
                            prompt = f"""
                            Evaluate Proficiency. Level: {user_data['current_level']}.
                            EXAM DATA: {json.dumps(data)}
                            ANSWERS: {json.dumps(st.session_state.exam_answers)}
                            OUTPUT JSON: {{ "level": "B1 High", "feedback": "TR feedback.", "breakdown": {{ "vocab": "Good", "grammar": "Fair", "reading": "Excellent", "speaking": "Good" }} }}
                            """
                            eval_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                            st.session_state.exam_result = strict_json_parse(eval_res.choices[0].message.content)
                            new_lvl = st.session_state.exam_result.get("level", "").split()[0]
                            if new_lvl and new_lvl != user_data["current_level"]:
                                user_data["current_level"] = new_lvl
                                save_data(user_data)
                                st.toast("Level Updated!")
                            st.session_state.exam_step = 5
                            st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        # 5. RESULTS & ANSWERS
        elif st.session_state.exam_step == 5:
            res = st.session_state.exam_result
            st.balloons()
            st.markdown(f"<h1 style='text-align:center'>🎓 Level: {res.get('level')}</h1>", unsafe_allow_html=True)
            st.info(res.get("feedback"))
            br = res.get("breakdown", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vocab", br.get("vocab", "-"))
            c2.metric("Grammar", br.get("grammar", "-"))
            c3.metric("Reading", br.get("reading", "-"))
            c4.metric("Speaking", br.get("speaking", "-"))
            
            st.divider()
            st.subheader("🔑 Answer Key")
            with st.expander("Show Answers"):
                st.markdown("#### Vocabulary")
                for i, q in enumerate(data.get("VOCABULARY", [])[:15]):
                    u = st.session_state.exam_answers.get(f"v_{i}", "-")
                    c = q['answer']
                    st.markdown(f"**Q{i+1}:** {q['question']}\nYou: {u} | Correct: **{c}** {'✅' if u==c else '❌'}\n---")
                st.markdown("#### Grammar")
                for i, q in enumerate(data.get("GRAMMAR", [])[:15]):
                    u = st.session_state.exam_answers.get(f"g_{i}", "-")
                    c = q['answer']
                    st.markdown(f"**Q{i+1}:** {q['sentence']}\nYou: {u} | Correct: **{c}**\n---")
                st.markdown("#### Reading")
                for i, q in enumerate(data.get("READING", {}).get("questions", [])[:5]):
                    u = st.session_state.exam_answers.get(f"r_{i}", "-")
                    c = q['answer']
                    st.markdown(f"**Q{i+1}:** {q['question']}\nYou: {u} | Correct: **{c}** {'✅' if u==c else '❌'}\n---")

            if st.button("Exit Exam"):
                st.session_state.exam_active = False
                st.rerun()

    # --- NORMAL SAYFALAR ---
    else:
        page = st.sidebar.radio("📌 Menu", ["🎭 Scenario Coach", "👂 Listening Quiz", "🧠 Vocab Gym (Anki)", "📜 History"])
        
        if page == "🎭 Scenario Coach":
            st.title("🗣️ AI Roleplay")
            
            if st.session_state.get("lesson_active", False) and not st.session_state.get("reading_phase", False):
                c1, c2 = st.columns([4,1])
                with c1: st.info(f"🎙️ Speaking | Target: {int(st.session_state.target_speaking_seconds//60)}m")
                with c2: 
                    if st.button("🚪 Quit"):
                        st.session_state.lesson_active = False
                        st.rerun()
                
                # Chat UI
                for m in st.session_state.get("display_messages", []):
                    if m["role"]=="info": st.info(m["content"])
                    elif m["role"]=="user": 
                        with st.chat_message("user"): st.write(m["content"])
                        if "correction" in m: st.warning(f"Correction: {m['correction']}")
                    elif m["role"]=="assistant":
                        with st.chat_message("assistant"):
                            st.write(m["content"])
                            with st.expander("TR"): st.info(m.get("tr_content",""))
                
                # iPhone Uyumlu Audio
                if st.session_state.get("last_audio_response"):
                    # Sadece son mesajın sesi tekrar etmesin diye kontrol
                    if st.session_state.get("played_audio_id") != len(st.session_state.messages):
                        autoplay_audio(st.session_state.last_audio_response)
                        st.session_state.played_audio_id = len(st.session_state.messages)

                audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️")
                if audio:
                    bio = io.BytesIO(audio['bytes']); bio.name = "audio.webm"
                    try:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=bio, response_format="verbose_json")
                        txt = trans.text
                        st.session_state.accumulated_speaking_time += trans.duration
                        
                        last_q = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
                        check_p = f"User said: '{txt}' to '{last_q}'. Fix grammar. If past tense required by question, force it. Return 'Correction: ...' or 'OK'."
                        corr_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":check_p}])
                        corr = corr_res.choices[0].message.content if "Correction:" in corr_res.choices[0].message.content else None
                        
                        st.session_state.messages.append({"role":"user", "content":txt})
                        disp = {"role":"user", "content":txt}
                        if corr: disp["correction"] = corr.replace("Correction:", "").strip()
                        st.session_state.display_messages.append(disp)
                        
                        rep_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                        reply = rep_res.choices[0].message.content
                        tr_reply = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"Translate: {reply}"}]).choices[0].message.content
                        
                        st.session_state.messages.append({"role":"assistant", "content":reply})
                        st.session_state.display_messages.append({"role":"assistant", "content":reply, "tr_content":tr_reply})
                        
                        tts = gTTS(text=reply, lang='en')
                        fp = io.BytesIO(); tts.write_to_fp(fp)
                        st.session_state.last_audio_response = fp.getvalue()
                        st.rerun()
                    except: st.error("Error processing audio")

                curr = st.session_state.accumulated_speaking_time
                targ = st.session_state.target_speaking_seconds
                st.progress(min(curr/targ, 1.0) if targ>0 else 0)
                if curr >= targ:
                    if st.button("➡️ Go to Reading"):
                        st.session_state.reading_phase = True
                        prompt = f"Create a reading text (150 words) about {st.session_state.scenario} and 3 questions. JSON."
                        res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                        st.session_state.reading_content = strict_json_parse(res.choices[0].message.content)
                        st.rerun()

            elif not st.session_state.get("lesson_active", False):
                if st.button("🚀 Start New Scenario"):
                    start_lesson_logic(client, user_data['current_level'], "LESSON", 1.0)
                    st.rerun()
            
            else:
                st.markdown("### 📖 Reading Task")
                if st.button("🚪 Quit"): 
                    st.session_state.lesson_active = False; st.rerun()
                content = st.session_state.get("reading_content", {})
                st.info(content.get("text", ""))
                with st.form("read_lesson"):
                    ans = []
                    for i, q in enumerate(content.get("questions", [])):
                        ans.append(st.text_input(f"{q}"))
                    if st.form_submit_button("Finish"):
                        user_data["lessons_completed"] += 1
                        save_data(user_data)
                        st.session_state.lesson_active = False
                        st.success("Lesson Completed!")
                        st.rerun()

        elif page == "👂 Listening Quiz":
            st.title("👂 Listening")
            if st.button("🔊 New Audio"):
                prompt = "Generate a B1 sentence."
                res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                text = res.choices[0].message.content.replace('"','')
                st.session_state.quiz_text = text
                tts = gTTS(text=text, lang='en')
                fp = io.BytesIO(); tts.write_to_fp(fp)
                st.session_state.quiz_audio = fp.getvalue()
                st.session_state.quiz_checked = False
                st.rerun()
            
            if st.session_state.get("quiz_audio"):
                autoplay_audio(st.session_state.quiz_audio) # <--- FIX
                user_input = st.text_input("Type what you hear:")
                if st.button("Check"):
                    clean_c = re.sub(r'[^\w\s]', '', st.session_state.quiz_text).lower()
                    clean_u = re.sub(r'[^\w\s]', '', user_input).lower()
                    if clean_u == clean_c: st.success("Correct!")
                    else: st.error(f"Wrong. Correct: {st.session_state.quiz_text}")

        elif page == "🧠 Vocab Gym (Anki)":
            st.title("🧠 Vocab Gym")
            if st.button("🚪 Quit"): st.session_state.srs_active_card = None; st.rerun()
            if not st.session_state.get("srs_active_card"):
                card, type_ = get_next_srs_card(user_data, set())
                if card:
                    if type_ == "new":
                        p = f"Define '{card['word']}' (Level {user_data['current_level']}). JSON: {{'word':'{card['word']}', 'tr':'...', 'ex':'...'}}"
                        res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}])
                        st.session_state.srs_active_card = strict_json_parse(res.choices[0].message.content)
                        st.session_state.srs_is_new = True
                    else:
                        st.session_state.srs_active_card = card
                        st.session_state.srs_is_new = False
                    tts = gTTS(text=st.session_state.srs_active_card['word'], lang='en')
                    fp = io.BytesIO(); tts.write_to_fp(fp)
                    st.session_state.srs_audio = fp.getvalue()
                else: st.info("No words due.")

            if st.session_state.get("srs_active_card"):
                c = st.session_state.srs_active_card
                st.markdown(f"## {c['word']}")
                if st.session_state.get("srs_audio"): 
                    autoplay_audio(st.session_state.srs_audio) # <--- FIX
                
                if st.button("Show Answer"): st.session_state.srs_revealed = True; st.rerun()
                if st.session_state.get("srs_revealed"):
                    st.success(c.get("tr")); st.info(c.get("ex"))
                    c1,c2,c3,c4 = st.columns(4)
                    if c1.button("Again"): update_srs_card_sm2(user_data, c, 0); st.session_state.srs_active_card=None; st.session_state.srs_revealed=False; st.rerun()
                    if c2.button("Hard"): update_srs_card_sm2(user_data, c, 3); st.session_state.srs_active_card=None; st.session_state.srs_revealed=False; st.rerun()
                    if c3.button("Good"): update_srs_card_sm2(user_data, c, 4); st.session_state.srs_active_card=None; st.session_state.srs_revealed=False; st.rerun()
                    if c4.button("Easy"): update_srs_card_sm2(user_data, c, 5); st.session_state.srs_active_card=None; st.session_state.srs_revealed=False; st.rerun()

        elif page == "📜 History":
            st.title("📜 History")
            for h in reversed(user_data.get("lesson_history", [])):
                st.write(f"{h.get('date')} - {h.get('topic')}")
else:
    st.warning("Enter API Key")
