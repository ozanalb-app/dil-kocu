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
st.set_page_config(page_title="Pınar's Friend v21", page_icon="🛡️", layout="wide")
DATA_FILE = "user_data.json"

# --- HALÜSİNASYON FİLTRESİ ---
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching", 
    "Copyright", "Subscribe", "Amara.org", "Watch this video", "You", 
    "I could not think of anything", "Silence", "Bye", "MBC", "Al Jazeera",
    "Caption", "Subtitle"
]

# --- 2. SENARYO HAVUZU ---
SCENARIO_POOL = [
    "Checking into a Hotel", "Ordering Coffee with Specific Milk", "Job Interview: Tell me about yourself",
    "Doctor's Appointment: I have a headache", "Returning a Shirt at a Store", "Asking for Directions in a New City",
    "Chatting with a Taxi Driver", "Immigration Control at the Airport", "Complaining about Cold Food in a Restaurant",
    "Booking a Table for Dinner", "Reporting a Lost Credit Card", "Opening a Bank Account",
    "Buying a Train Ticket", "Explaining a Project to a Boss", "Negotiating Salary",
    "Parent-Teacher Meeting", "Calling Tech Support for Internet Issues", "Describing a Witnessed Crime to Police",
    "Buying Medicine at a Pharmacy", "Inviting a Friend to a Movie", "Refusing an Invitation Politely",
    "Asking a Neighbor to Turn Down Music", "Hairdresser: Explaining the Cut", "Renting a Car",
    "Check-in at the Airport", "Discussing Weekend Plans", "Borrowing a Book from the Library",
    "Buying Groceries at the Market", "Asking for a Refund", "Introducing Yourself to New Neighbors",
    "Apologizing for Being Late", "Asking for Help in a Supermarket", "Gym Membership Inquiry",
    "Talking about the Weather with a Stranger", "Buying a SIM Card", "Ordering Pizza by Phone",
    "Job Interview: Weaknesses", "Discussing Movie Preferences", "Planning a Surprise Party",
    "Reporting a Car Accident", "Real Estate: Viewing an Apartment", "Veterinarian: Sick Pet",
    "IT Help: Computer Won't Start", "Hotel: Asking for Extra Towels", "Restaurant: Splitting the Bill",
    "Giving Advice to a Friend", "Talking about Hobbies", "Post Office: Sending a Package",
    "Museum: Buying Tickets", "Bus Station: Which Bus Goes to Center?"
]

VOCAB_POOL = {
    "A2": ["able", "about", "above", "accept", "accident", "adventure", "agree", "allow", "angry", "answer", "apple", "arrive", "ask", "baby", "back", "bad", "bag", "ball", "bank", "beautiful", "because", "become", "bed", "begin", "believe", "big", "bird", "black", "blue", "boat", "body", "book", "boring", "borrow", "box", "boy", "bread", "break", "breakfast", "bring", "brother", "build", "bus", "business", "buy", "call", "camera", "car", "card", "care", "carry", "cat", "catch", "cause", "change", "cheap", "check", "child", "choose", "city", "clean", "clear", "climb", "clock", "close", "clothes", "cloud", "coffee", "cold", "color", "come", "company", "compare", "complete", "computer", "cook", "cool", "copy", "corner", "correct", "cost", "count", "country", "course", "cousin", "cover", "crazy", "cream", "create", "cross", "cry", "cup", "cut", "dance", "dark", "date", "daughter", "day", "dead", "deal", "dear", "death", "decide"],
    "B1": ["achieve", "action", "active", "activity", "admire", "admit", "adult", "advice", "afford", "afraid", "after", "against", "age", "agency", "agent", "ago", "agree", "agreement", "ahead", "aim", "air", "alarm", "alive", "all", "allow", "ally", "alone", "along", "already", "also", "alter", "alternative", "although", "always", "amazed", "amazing", "ambition", "among", "amount", "analyse", "analysis", "ancient", "and", "anger", "angle", "angry", "animal", "announce", "annoy", "annual", "another", "answer", "anxious", "any", "apart", "apartment", "apologize", "appear", "appearance", "apple", "application", "apply", "appoint", "appreciate", "approach", "appropriate", "approve", "area", "argue", "argument", "arise", "arm", "army", "around", "arrange", "arrangement", "arrest", "arrival", "arrive", "art", "article", "artificial", "artist", "artistic", "ashamed", "asleep", "ask", "aspect", "assess", "assessment", "assignment", "assist", "assistant", "associate", "association", "assume", "assumption", "atmosphere", "attach", "attack", "attempt"],
    "B2": ["abandon", "absolute", "absorb", "abstract", "academic", "access", "accidental", "accompany", "account", "accurate", "accuse", "achieve", "acquire", "act", "action", "active", "actual", "adapt", "add", "addition", "additional", "address", "adequate", "adjust", "administration", "admire", "admission", "admit", "adopt", "adult", "advance", "advanced", "advantage", "adventure", "advertise", "advice", "advise", "affair", "affect", "afford", "afraid", "after", "afternoon", "afterwards", "again", "against", "age", "agency", "agenda", "agent", "aggressive", "ago", "agree", "agreement", "agriculture", "ahead", "aid", "aim", "air", "aircraft", "airline", "airport", "alarm", "album", "alcohol", "alive", "all", "allow", "allowance", "ally", "almost", "alone", "along", "alongside", "already", "also", "alter", "alternative", "although", "altogether", "always", "amaze", "amazed", "amazing", "ambition", "ambulance", "among", "amount", "amuse", "analyse", "analysis", "ancient", "and", "anger", "angle", "angry", "animal", "ankle"]
}

# --- 3. YARDIMCI FONKSİYONLAR ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "current_level": "A2", 
            "lessons_completed": 0, 
            "exam_scores": [], 
            "vocabulary_bank": [], 
            "completed_scenarios": [],
            "rotated_vocab": {"A2": [], "B1": [], "B2": []},
            "lesson_history": [],
            "error_bank": [],
            "next_mode": "ASSESSMENT",
            "next_lesson_prep": None 
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        defaults = {
            "completed_scenarios": [], 
            "error_bank": [],
            "next_lesson_prep": None,
            "rotated_vocab": {"A2": [], "B1": [], "B2": []},
            "lesson_history": []
        }
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data

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

def determine_sub_level(level, lessons_completed):
    cycle = lessons_completed % 10
    if cycle < 3: return "Low"
    elif cycle < 7: return "Medium"
    else: return "High"

def get_relevant_vocab(client, scenario, available_vocab_list):
    # Eğer havuz boşsa veya çok azsa direkt döndür
    if not available_vocab_list or len(available_vocab_list) <= 5:
        return available_vocab_list if available_vocab_list else ["hello", "world", "practice", "english", "learn"]
        
    candidates = random.sample(available_vocab_list, min(50, len(available_vocab_list)))
    prompt = f"SCENARIO: {scenario}\nCANDIDATES: {', '.join(candidates)}\nSelect 5 relevant words. JSON ARRAY ONLY: ['w1', ...]"
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        parsed = strict_json_parse(res.choices[0].message.content)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
        else:
            return random.sample(candidates, 5)
    except:
        return random.sample(candidates, 5)

user_data = load_data()

# --- 4. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    assigned_scenario = None
    assigned_vocab = []
    
    # 🔥 DÜZELTME: Ödevi hemen tüket
    if mode == "LESSON" and user_data.get("next_lesson_prep"):
        plan = user_data["next_lesson_prep"]
        assigned_scenario = plan.get("scenario", plan.get("topic"))
        assigned_vocab = plan.get("vocab", [])
        
        # Kullanıldıktan hemen sonra SİL ki döngüye girmesin
        user_data["next_lesson_prep"] = None
        save_data(user_data)
        st.toast(f"📅 Loaded Plan: {assigned_scenario}", icon="✅")

    if mode == "EXAM":
        scenario = random.choice(SCENARIO_POOL)
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. SCENARIO: {scenario}. CRITICAL: Ask concise questions. Do not give feedback."
    elif mode == "ASSESSMENT":
        scenario = "Placement Interview"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions ONE BY ONE."
    else:
        if assigned_scenario:
            scenario = assigned_scenario
        else:
            completed = user_data.get("completed_scenarios", [])
            available = [s for s in SCENARIO_POOL if s not in completed]
            
            # Havuz bittiyse sıfırla
            if not available:
                user_data["completed_scenarios"] = []
                save_data(user_data)
                available = SCENARIO_POOL
            
            scenario = random.choice(available)
            # Seçileni havuza işle
            if scenario not in user_data["completed_scenarios"]:
                user_data["completed_scenarios"].append(scenario)
                save_data(user_data)

        system_role = f"""
        ACT AS A ROLEPLAYER for: '{scenario}'. 
        LEVEL: {full_level_desc}.
        CRITICAL RULE: 
        1. Keep responses VERY SHORT (Max 25 words).
        2. NEVER say "Thank you for sharing" or "Good job".
        3. ALWAYS end with a relevant follow-up question to keep the roleplay going.
        """

    target_vocab = []
    if mode == "LESSON":
        if assigned_vocab: 
            target_vocab = assigned_vocab
        else:
            full_list = VOCAB_POOL.get(level, [])
            used = user_data["rotated_vocab"].get(level, [])
            avail = [w for w in full_list if w not in used]
            
            if len(avail) < 5:
                user_data["rotated_vocab"][level] = [] # Sıfırla
                avail = full_list
                save_data(user_data)
            
            target_vocab = get_relevant_vocab(client, scenario, avail)

    # Session State Reset
    st.session_state.lesson_active = True
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False
    st.session_state.final_report = None
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60 
    st.session_state.target_vocab = target_vocab
    st.session_state.scenario = scenario
    st.session_state.last_audio_bytes = None
    st.session_state.display_messages = []
    
    # Context Setter
    context_msg = f"🎭 **SCENARIO:** {scenario}\n🔑 **WORDS:** {', '.join(target_vocab)}"
    st.session_state.display_messages.append({"role": "info", "content": context_msg})

    intro_prompt = f"{system_role}\nStart the roleplay now with your first line."
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
    page = st.sidebar.radio("📌 Menu", ["🎭 Scenario Coach", "👂 Listening Quiz", "🏋️ Vocab Gym", "📜 History"])

    with st.sidebar:
        st.divider()
        st.markdown("### 🚨 Error Bank")
        errors = user_data.get("error_bank", [])
        if not errors: st.caption("No errors recorded yet.")
        else:
            for e in reversed(errors[-3:]):
                st.error(f"❌ {e['wrong']}\n✅ {e['correct']}")
            if len(errors) > 3: st.caption(f"...and {len(errors)-3} more.")
            if st.button("🗑️ Clear"):
                user_data["error_bank"] = []
                save_data(user_data)
                st.rerun()

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

    # --- VOCAB GYM ---
    elif page == "🏋️ Vocab Gym":
        st.title("🏋️ Vocabulary Gym")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 New Card"):
                pool = VOCAB_POOL.get(user_data["current_level"], ["hello"])
                pool_copy = list(pool)
                random.shuffle(pool_copy)
                word = random.choice(pool_copy)
                st.session_state.flashcard_word = word
                st.session_state.flashcard_revealed = False
                
                tts = gTTS(text=word, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.session_state.vocab_audio = fp.getvalue()
        
        if "flashcard_word" in st.session_state and st.session_state.flashcard_word:
            st.markdown(f"<h1 style='text-align: center; color:#4F8BF9'>{st.session_state.flashcard_word}</h1>", unsafe_allow_html=True)
            if "vocab_audio" in st.session_state:
                st.audio(st.session_state.vocab_audio, format='audio/mp3', autoplay=True)

            if not st.session_state.flashcard_revealed:
                if st.button("👀 Show Meaning"):
                    st.session_state.flashcard_revealed = True
                    prompt = f"Define '{st.session_state.flashcard_word}' in Turkish + Example. JSON: {{'tr':'...', 'ex':'...'}}"
                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                    st.session_state.card_data = strict_json_parse(res.choices[0].message.content)
                    st.rerun()
            else:
                d = st.session_state.card_data
                st.success(f"🇹🇷 {d.get('tr','')}")
                st.info(f"🇬🇧 {d.get('ex','')}")

    # --- HISTORY ---
    elif page == "📜 History":
        st.title("📜 History")
        hist = user_data.get("lesson_history", [])
        if not hist: st.info("No history.")
        for h in reversed(hist):
            with st.expander(f"📚 {h.get('date')} - {h.get('topic')}"):
                st.write(f"**Score:** {h.get('score')}")
                st.caption(f"Speak: {h.get('speaking_score')} | Read: {h.get('reading_score')}")
                st.warning(f"**Grammar Needs:**\n" + "\n".join([f"- {t}" for t in h.get('grammar_topics', [])]))

    # --- SCENARIO COACH ---
    elif page == "🎭 Scenario Coach":
        st.title("🗣️ AI Roleplay Coach")
        with st.sidebar:
            st.divider()
            sub = determine_sub_level(user_data['current_level'], user_data['lessons_completed'])
            c1, c2 = st.columns(2)
            with c1: st.metric("Level", user_data['current_level'])
            with c2: st.metric("Band", sub)
            
            if st.session_state.get("lesson_active", False) and not st.session_state.get("reading_phase", False):
                curr = st.session_state.accumulated_speaking_time
                targ = st.session_state.target_speaking_seconds
                prog = min(curr/targ, 1.0) if targ > 0 else 0
                c_min = int(curr // 60)
                c_sec = int(curr % 60)
                t_min = int(targ // 60)
                t_sec = int(targ % 60)
                st.progress(prog, text=f"Time: {c_min}m {c_sec}s / {t_min}m {t_sec}s")

        if not st.session_state.get("lesson_active", False):
            if user_data.get("next_lesson_prep"):
                prep = user_data.get("next_lesson_prep", {})
                sc_name = prep.get("scenario", prep.get("topic", "Unknown"))
                st.success(f"🎯 Next: {sc_name}")
            mins = st.slider("Duration (Mins)", 0.5, 30.0, 1.0, step=0.5)
            if st.button("🚀 START SCENARIO"):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], mins)
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
                                with st.expander("🛠️ Grammar Check", expanded=True):
                                    st.markdown(f":red[{msg['correction']}]")
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
                                            content = re.sub(f"(?i)\\b{w}\\b", f"**:{'blue'}[{w.upper()}]**", content)
                                        st.markdown(content)
                                    with st.expander("🇹🇷 Türkçesi"):
                                        st.info(msg.get("tr_content", "..."))
                            else:
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.write(msg["content"])

                if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
                    st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

                st.write("---")
                if st.button("🆘 Hints"):
                    with st.spinner("..."):
                        hist = st.session_state.messages[-4:]
                        prompt = "Give 3 short English reply options suitable for this scenario."
                        res = client.chat.completions.create(model="gpt-4o", messages=hist+[{"role":"user","content":prompt}])
                        st.info(res.choices[0].message.content)

                c1, c2 = st.columns([1,4])
                with c1: audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️")
                with c2:
                    curr = st.session_state.accumulated_speaking_time
                    targ = st.session_state.target_speaking_seconds
                    
                    # 🔥 DÜZELTME: Süre Kontrolü ve Geçiş Engeli
                    time_up = (curr >= targ)
                    btn_text = "➡️ UNLOCK READING" if not time_up else "➡️ GO TO READING PHASE"
                    
                    if st.button(btn_text, use_container_width=True, disabled=False):
                        if user_data["next_mode"] != "ASSESSMENT" and not time_up:
                            st.toast("⏳ Not yet! Keep speaking to unlock.", icon="🔒")
                        else:
                            st.session_state.reading_phase = True
                            with st.spinner("Generating reading task..."):
                                prompt = f"Create A2/B1 reading text about the scenario: {st.session_state.scenario}. Then 3 questions. JSON: {{'text':'...','questions':['Q1','Q2','Q3']}}"
                                try:
                                    res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                                    st.session_state.reading_content = strict_json_parse(res.choices[0].message.content)
                                    # Fallback
                                    if not st.session_state.reading_content:
                                        st.session_state.reading_content = {"text": f"Reading regarding {st.session_state.scenario}...", "questions": ["Question 1?", "Question 2?", "Question 3?"]}
                                except:
                                    st.session_state.reading_content = {"text": "Error loading text.", "questions": ["Q1", "Q2", "Q3"]}
                            st.rerun()

                if audio:
                    if "last_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_bytes:
                        st.session_state.last_bytes = audio['bytes']
                        if len(audio['bytes']) < 2000:
                            st.warning("Audio unclear. Try again.")
                        else:
                            with st.spinner("Processing..."):
                                try:
                                    bio = io.BytesIO(audio['bytes'])
                                    bio.name = "audio.webm"
                                    txt = client.audio.transcriptions.create(
                                        model="whisper-1", file=bio, language="en", temperature=0.2,
                                        prompt=f"User speaking about scenario {st.session_state.scenario}."
                                    ).text
                                    
                                    bad = any(b.lower() in txt.lower() for b in BANNED_PHRASES)
                                    if bad or len(txt.strip()) < 2:
                                        st.warning("Audio unclear.")
                                    else:
                                        st.session_state.accumulated_speaking_time += len(txt.split()) * 0.7
                                        
                                        corr = None
                                        try:
                                            p_check = f"Check '{txt}'. IGNORE small errors. If MAJOR error, return 'Düzeltme: [Correct]'. Else 'OK'."
                                            c_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p_check}])
                                            ans = c_res.choices[0].message.content
                                            if "Düzeltme:" in ans:
                                                corr = ans
                                                user_data["error_bank"].append({"wrong": txt, "correct": corr.replace("Düzeltme:", "").strip()})
                                                save_data(user_data)
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

            # OKUMA FAZI
            else:
                if not st.session_state.get("reading_completed", False):
                    st.markdown("### 📖 Reading")
                    content = st.session_state.get("reading_content", {})
                    st.info(content.get("text", ""))
                    
                    with st.form("read_form"):
                        ans_list = []
                        questions = content.get("questions", ["Q1", "Q2", "Q3"])
                        for i, q in enumerate(questions):
                            ans_list.append(st.text_input(f"{i+1}. {q}"))
                        submitted = st.form_submit_button("🏁 FINISH")
                    
                    if submitted:
                        with st.spinner("Analyzing..."):
                            prompt = """
                            Analyze Speaking & Reading.
                            SCORING: score = (speak_score*0.8) + (read_score*0.2).
                            FEEDBACK (IN TURKISH): pros, cons, grammar_topics, suggestions.
                            NEXT LESSON: New scenario + 5 words.
                            JSON: {
                                "score": 0, "speaking_score": 0, "reading_score": 0,
                                "reading_feedback": [{"question":"...","user_answer":"...","correct_answer":"...","is_correct":true}],
                                "learned_words": [], "pros": [], "cons": [], "grammar_topics": [], "suggestions": [],
                                "next_lesson_homework": {"scenario": "...", "vocab": []}
                            }
                            """
                            user_json = json.dumps({f"Q{i}": a for i,a in enumerate(ans_list)})
                            msgs = st.session_state.messages + [{"role":"user","content":f"Reading Answers: {user_json}"}, {"role":"system","content":prompt}]
                            
                            try:
                                res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                                rep = strict_json_parse(res.choices[0].message.content)
                                if not rep: rep = {"score": 70} 

                                user_data["lessons_completed"] += 1
                                user_data["rotated_vocab"][user_data["current_level"]].extend(st.session_state.target_vocab)
                                if "next_lesson_homework" in rep: user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                                
                                hist = {
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "topic": st.session_state.scenario,
                                    "score": rep.get("score"),
                                    "speaking_score": rep.get("speaking_score"),
                                    "reading_score": rep.get("reading_score"),
                                    "grammar_topics": rep.get("grammar_topics", []),
                                    "words": st.session_state.target_vocab,
                                    "feedback_pros": rep.get("pros", []),
                                    "feedback_cons": rep.get("cons", [])
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
                    st.markdown(f"## 📊 Score: {rep.get('score')} (🗣️{rep.get('speaking_score')} | 📖{rep.get('reading_score')})")
                    
                    for fb in rep.get("reading_feedback", []):
                        color = "green" if fb["is_correct"] else "red"
                        with st.expander(f"Question: {fb['question']}"):
                            st.write(f"You: {fb['user_answer']}")
                            st.markdown(f":{color}[Correct: {fb['correct_answer']}]")

                    c1, c2 = st.columns(2)
                    with c1: st.success("\n".join(rep.get('pros', [])))
                    with c2: st.error("\n".join(rep.get('cons', [])))
                    
                    if rep.get('grammar_topics'):
                        st.warning("**Çalış:** " + ", ".join(rep.get('grammar_topics')))
                        
                    next_sc = rep.get('next_lesson_homework', {}).get('scenario', 'Next Level')
                    st.info(f"**Next:** {next_sc}")
                    
                    if st.button("🚀 START NEXT"):
                        st.session_state.messages = []
                        st.session_state.display_messages = []
                        st.session_state.reading_phase = False
                        st.session_state.reading_completed = False
                        st.session_state.final_report = None
                        st.session_state.accumulated_speaking_time = 0
                        st.rerun()
else:
    st.warning("Enter API Key")
