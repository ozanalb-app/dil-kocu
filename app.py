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
st.set_page_config(page_title="Pınar's Friend v16.1", page_icon="🇹🇷", layout="wide")
DATA_FILE = "user_data.json"

# --- HALÜSİNASYON FİLTRESİ ---
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching", 
    "Copyright", "Subscribe", "Amara.org", "Watch this video", "You", 
    "I could not think of anything", "Silence", "Bye", "MBC", "Al Jazeera",
    "Caption", "Subtitle"
]

# --- 2. VERİ HAVUZLARI ---
TOPIC_POOL = {
    "A2": ["My Daily Routine", "Shopping", "Food", "Family", "Hobbies", "Weather", "My City", "Holiday", "School", "Weekend"],
    "B1": ["Job Interview", "Travel Problems", "Technology", "Health", "Social Media", "Education", "Culture", "Future Plans", "Environment", "Friendship"],
    "B2": ["Global Warming", "Remote Work", "AI Ethics", "Economy", "Globalization", "Leadership", "Mental Health", "Privacy", "Migration", "Innovation"]
}

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
            "completed_topics": [],
            "rotated_vocab": {"A2": [], "B1": [], "B2": []},
            "lesson_history": [],
            "next_mode": "ASSESSMENT",
            "next_lesson_prep": None 
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        defaults = {
            "completed_topics": [], 
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

def get_relevant_vocab(client, topic, available_vocab_list):
    if len(available_vocab_list) <= 5: return available_vocab_list
    candidates = random.sample(available_vocab_list, min(50, len(available_vocab_list)))
    prompt = f"TOPIC: {topic}\nCANDIDATES: {', '.join(candidates)}\nSelect 5 relevant words. JSON ARRAY ONLY: ['w1', ...]"
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        return strict_json_parse(res.choices[0].message.content)
    except:
        return random.sample(candidates, 5)

user_data = load_data()

# --- 4. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    assigned_topic = None
    assigned_vocab = []
    
    if mode == "LESSON" and user_data.get("next_lesson_prep"):
        plan = user_data["next_lesson_prep"]
        assigned_topic = plan.get("topic")
        assigned_vocab = plan.get("vocab", [])
        st.toast(f"📅 Planned Topic: {assigned_topic}", icon="✅")

    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. TOPIC: {topic}. GOAL: Test. RESPONSE: Short questions."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions."
    else:
        if assigned_topic:
            topic = assigned_topic
        else:
            all_topics = TOPIC_POOL.get(level, ["General"])
            completed = user_data.get("completed_topics", [])
            available = [t for t in all_topics if t not in completed]
            if not available:
                user_data["completed_topics"] = []
                save_data(user_data)
                available = all_topics
            topic = random.choice(available)
            if topic not in user_data["completed_topics"]:
                user_data["completed_topics"].append(topic)
                save_data(user_data)

        system_role = f"ACT AS: Helpful Coach. LEVEL: {full_level_desc}. TOPIC: {topic}. RULE: Answers < 2 sentences. ALWAYS ask a follow-up question."

    target_vocab = []
    if mode == "LESSON":
        if assigned_vocab: target_vocab = assigned_vocab
        else:
            full_list = VOCAB_POOL.get(level, [])
            used = user_data["rotated_vocab"].get(level, [])
            avail = [w for w in full_list if w not in used]
            if len(avail) < 5:
                user_data["rotated_vocab"][level] = []
                avail = full_list
                save_data(user_data)
            target_vocab = get_relevant_vocab(client, topic, avail)

    st.session_state.lesson_active = True
    st.session_state.reading_phase = False
    st.session_state.reading_completed = False # 🔥 YENİ: Okuma bitti mi kontrolü
    st.session_state.final_report = None # 🔥 YENİ: Raporu saklamak için
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60 
    st.session_state.target_vocab = target_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    
    # Başlangıç
    intro = f"Start by saying 'Hello Pınar! Today's topic is {topic}'."
    prompt = f"{system_role}\n{intro}\nCONTEXT: {', '.join(target_vocab)}"
    st.session_state.messages = [{"role": "system", "content": prompt}]
    
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        msg = res.choices[0].message.content
        
        tr_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": f"Translate to Turkish: {msg}"}])
        tr_msg = tr_res.choices[0].message.content
        
        st.session_state.messages.append({"role": "assistant", "content": msg, "tr_content": tr_msg})
        
        tts = gTTS(text=msg, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.session_state.last_audio_response = fp.getvalue()
        
        if mode == "LESSON" and user_data.get("next_lesson_prep"):
            user_data["next_lesson_prep"] = None
            save_data(user_data)
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.lesson_active = False

# --- 5. ARAYÜZ ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)
    page = st.sidebar.radio("📌 Menu", ["🎤 AI Coach", "🏋️ Vocab Gym", "📜 History"])

    # --- VOCAB GYM ---
    if page == "🏋️ Vocab Gym":
        st.title("🏋️ Vocabulary Gym")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 New Card"):
                pool = VOCAB_POOL.get(user_data["current_level"], ["hello"])
                st.session_state.flashcard_word = random.choice(pool)
                st.session_state.flashcard_revealed = False
        
        if "flashcard_word" in st.session_state and st.session_state.flashcard_word:
            st.markdown(f"<h1 style='text-align: center; color:#4F8BF9'>{st.session_state.flashcard_word}</h1>", unsafe_allow_html=True)
            if not st.session_state.flashcard_revealed:
                if st.button("👀 Show Meaning"):
                    st.session_state.flashcard_revealed = True
                    prompt = f"Define '{st.session_state.flashcard_word}' in Turkish + 1 English Example. JSON: {{'tr':'...', 'ex':'...'}}"
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

    # --- MAIN COACH ---
    elif page == "🎤 AI Coach":
        st.title("🗣️ AI Personal Coach")
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
                st.progress(prog, text=f"Speaking: {c_min}m {c_sec}s / {t_min}m {t_sec}s")

        if not st.session_state.get("lesson_active", False):
            if user_data.get("next_lesson_prep"):
                st.success(f"🎯 Next: {user_data['next_lesson_prep']['topic']}")
            mins = st.slider("Duration (Mins)", 0.5, 30.0, 1.0, step=0.5)
            if st.button("🚀 START"):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], mins)
                st.rerun()
        else:
            # KONUŞMA FAZI
            if not st.session_state.get("reading_phase", False):
                chat_cont = st.container()
                with chat_cont:
                    for i, msg in enumerate(st.session_state.messages):
                        if msg["role"] != "system":
                            is_last = (i == len(st.session_state.messages) - 1)
                            is_bot = (msg["role"] == "assistant")
                            
                            if msg["role"] == "user" and "correction" in msg:
                                with st.expander("🛠️ Grammar Check", expanded=True):
                                    st.markdown(f":red[{msg['correction']}]")

                            if is_bot:
                                if is_last:
                                    with st.chat_message("assistant", avatar="🤖"):
                                        st.write("🔊 **Listening Mode...**")
                                        with st.expander("🇬🇧 English Text"):
                                            content = msg["content"]
                                            for w in st.session_state.target_vocab:
                                                content = re.sub(f"(?i)\\b{w}\\b", f"**:{'blue'}[{w.upper()}]**", content)
                                            st.markdown(content)
                                        with st.expander("🇹🇷 Türkçesi"):
                                            st.info(msg.get("tr_content", "Çeviri hazırlanıyor..."))
                                else:
                                    with st.chat_message("assistant", avatar="🤖"):
                                        st.write(msg["content"])
                            elif msg["role"] == "user":
                                with st.chat_message("user", avatar="👤"):
                                    st.write(msg["content"])

                if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
                    st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

                st.write("---")
                if st.button("🆘 Help Me Say Something"):
                    with st.spinner("..."):
                        hist = st.session_state.messages[-4:]
                        prompt = "Give 3 short English reply options. Format: 1. ... 2. ... 3. ..."
                        res = client.chat.completions.create(model="gpt-4o", messages=hist+[{"role":"user","content":prompt}])
                        st.info(res.choices[0].message.content)

                c1, c2 = st.columns([1,4])
                with c1: audio = mic_recorder(start_prompt="🎤", stop_prompt="⏹️")
                with c2:
                    curr = st.session_state.accumulated_speaking_time
                    targ = st.session_state.target_speaking_seconds
                    if st.button("➡️ READING PHASE", use_container_width=True):
                        if user_data["next_mode"]!="ASSESSMENT" and curr < targ:
                            st.toast("Time not up!", icon="⏳")
                        else:
                            st.session_state.reading_phase = True
                            prompt = f"Create A2/B1 reading text about {st.session_state.topic}. Then 3 questions. JSON: {{'text':'...','questions':['Q1','Q2','Q3']}}"
                            res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}])
                            st.session_state.reading_content = strict_json_parse(res.choices[0].message.content)
                            st.rerun()

                if audio:
                    if "last_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_bytes:
                        st.session_state.last_bytes = audio['bytes']
                        with st.spinner("Processing..."):
                            bio = io.BytesIO(audio['bytes'])
                            bio.name = "audio.webm"
                            txt = client.audio.transcriptions.create(
                                model="whisper-1", file=bio, language="en", temperature=0.2,
                                prompt=f"User speaking about {st.session_state.topic}."
                            ).text
                            
                            bad = any(b.lower() in txt.lower() for b in BANNED_PHRASES)
                            if bad or len(txt.strip()) < 2:
                                st.warning("Audio unclear.")
                            else:
                                st.session_state.accumulated_speaking_time += len(txt.split()) * 0.7
                                
                                # 🔥 GEVŞEK VE TÜRKÇE GRAMER KONTROLÜ
                                corr = None
                                try:
                                    p_check = f"Check '{txt}'. Ignore 'the', 'a', 'an' and punctuation. If MAJOR error (tense/verb), return 'Düzeltme: [Correct Sentence]'. Else return 'OK'."
                                    c_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p_check}])
                                    if "Düzeltme:" in c_res.choices[0].message.content:
                                        corr = c_res.choices[0].message.content
                                except: pass

                                u_msg = {"role": "user", "content": txt}
                                if corr: u_msg["correction"] = corr
                                st.session_state.messages.append(u_msg)
                                
                                res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                                rep = res.choices[0].message.content
                                tr_rep = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":f"Translate to Turkish: {rep}"}]).choices[0].message.content
                                
                                st.session_state.messages.append({"role": "assistant", "content": rep, "tr_content": tr_rep})
                                
                                tts = gTTS(text=rep, lang='en')
                                fp = io.BytesIO()
                                tts.write_to_fp(fp)
                                st.session_state.last_audio_response = fp.getvalue()
                                st.rerun()

            # OKUMA FAZI (HATA DÜZELTİLDİ: STATE KULLANIMI)
            else:
                # 🔥 EĞER RAPOR OLUŞMADIYSA FORMU GÖSTER
                if not st.session_state.get("reading_completed", False):
                    st.markdown("### 📖 Reading")
                    content = st.session_state.get("reading_content", {})
                    st.info(content.get("text", ""))
                    
                    with st.form("read_form"):
                        ans_list = []
                        for i, q in enumerate(content.get("questions", [])):
                            ans_list.append(st.text_input(f"{i+1}. {q}"))
                        submitted = st.form_submit_button("🏁 FINISH")
                    
                    if submitted:
                        with st.spinner("Analyzing..."):
                            prompt = """
                            Analyze Speaking & Reading.
                            SCORING: score = (speak_score*0.8) + (read_score*0.2).
                            FEEDBACK (IN TURKISH): pros, cons, grammar_topics, suggestions.
                            NEXT LESSON: New topic + 5 words.
                            JSON: {
                                "score": 0, "speaking_score": 0, "reading_score": 0,
                                "reading_feedback": [{"question":"...","user_answer":"...","correct_answer":"...","is_correct":true}],
                                "learned_words": [], "pros": [], "cons": [], "grammar_topics": [], "suggestions": [],
                                "next_lesson_homework": {"topic": "...", "vocab": []}
                            }
                            """
                            user_json = json.dumps({f"Q{i}": a for i,a in enumerate(ans_list)})
                            msgs = st.session_state.messages + [{"role":"user","content":f"Reading Answers: {user_json}"}, {"role":"system","content":prompt}]
                            
                            res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                            rep = strict_json_parse(res.choices[0].message.content)
                            if not rep: rep = {"score": 70} 

                            # Kaydet ve State Güncelle
                            user_data["lessons_completed"] += 1
                            user_data["rotated_vocab"][user_data["current_level"]].extend(st.session_state.target_vocab)
                            if "next_lesson_homework" in rep: user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                            
                            hist = {
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "topic": st.session_state.topic,
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
                            
                            # State'e at ve yenile
                            st.session_state.final_report = rep
                            st.session_state.reading_completed = True
                            st.rerun()
                
                # 🔥 EĞER RAPOR VARSA SONUÇ EKRANINI GÖSTER
                else:
                    rep = st.session_state.final_report
                    st.balloons()
                    st.markdown(f"## 📊 Score: {rep.get('score')} (🗣️{rep.get('speaking_score')} | 📖{rep.get('reading_score')})")
                    
                    # Reading detayları
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
                        
                    st.info(f"**Next:** {rep.get('next_lesson_homework', {}).get('topic')}")
                    
                    if st.button("🚀 START NEXT"):
                        st.session_state.messages = []
                        st.session_state.reading_phase = False
                        st.session_state.reading_completed = False
                        st.session_state.final_report = None
                        st.session_state.accumulated_speaking_time = 0
                        st.rerun()
else:
    st.warning("Enter API Key")
