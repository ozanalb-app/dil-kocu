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
st.set_page_config(page_title="Pınar's Friend v10 (Smart Vocab)", page_icon="🧠", layout="wide")
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
    "A2": [
        "My Daily Morning Routine", "What I Do in the Evening", "Ordering Food at a Restaurant",
        "Asking for Directions in a City", "Shopping for Clothes", "Buying Food at the Supermarket",
        "My Favorite Food", "Parent Teacher Meeting", "My Favorite Music", "My Best Friend", "My Family",
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

# GENİŞLETİLMİŞ KELİME HAVUZU
VOCAB_POOL = {
    "A2": [
        "able", "about", "above", "across", "afraid", "after", "again", "against", "age", "ago",
        "agree", "air", "all", "allow", "almost", "alone", "along", "already", "also", "always",
        "among", "angry", "animal", "another", "answer", "any", "anyone", "appear", "apple", "area",
        "arm", "around", "arrive", "art", "ask", "baby", "back", "bad", "bag", "ball",
        "bank", "base", "bath", "be", "beach", "beautiful", "because", "become", "bed", "before",
        "begin", "behind", "believe", "below", "best", "better", "between", "big", "bird", "black",
        "blue", "board", "boat", "body", "book", "both", "bottom", "box", "boy", "bread",
        "break", "breakfast", "bring", "brother", "brown", "build", "bus", "business", "busy", "but",
        "buy", "cake", "call", "can", "car", "card", "care", "carry", "case", "cat", "friend", "family", "house", "food", "water", "school", "music", "movie", "city", "park"
    ],
    "B1": [
        "achieve", "action", "activity", "admit", "adult", "affect", "afford", "agency", "agent", "aim",
        "airline", "alive", "amount", "ancient", "angle", "announce", "anxious", "apart", "appeal", "appear",
        "apply", "approach", "approve", "argue", "arise", "arrange", "arrest", "arrival", "article", "ashamed",
        "asleep", "assist", "assume", "attack", "attempt", "attend", "attitude", "attract", "audience", "author",
        "average", "avoid", "awake", "award", "aware", "backwards", "bacon", "badge", "baggage", "baker",
        "balance", "ban", "bandage", "bar", "bargain", "barrier", "basic", "basis", "battle", "beauty",
        "behave", "belief", "belong", "belt", "beneath", "benefit", "beside", "bet", "beyond", "bicycle",
        "bid", "bill", "biology", "birth", "bitter", "blame", "blank", "blind", "block", "blood",
        "blow", "boil", "bomb", "bone", "bonus", "border", "bored", "borrow", "bother", "bottle", "opinion", "suggest", "experience", "prefer", "describe"
    ],
    "B2": [
        "abandon", "absolute", "academic", "acceptable", "accompany", "account", "accurate", "accuse", "acknowledge", "acquire",
        "actual", "adapt", "additional", "address", "administration", "adopt", "advance", "advantage", "adventure", "advertise",
        "adviser", "advocate", "affair", "affect", "afford", "aggressive", "agreement", "agriculture", "aid", "aircraft",
        "alarm", "alcohol", "alive", "alleged", "allowance", "ally", "alter", "alternative", "ambition", "analyse",
        "analysis", "anger", "angle", "anniversary", "announce", "annual", "anticipate", "anxiety", "apologize", "apparent",
        "appeal", "appearance", "appoint", "appreciate", "appropriate", "approval", "approve", "approximately", "architect", "architecture",
        "argue", "arise", "armed", "aspect", "assault", "assert", "assess", "assessment", "asset", "assign",
        "assistance", "assistant", "associate", "association", "assume", "assumption", "assure", "atmosphere", "attach", "attachment",
        "attempt", "attend", "attention", "attitude", "attorney", "attract", "attraction", "attribute", "audience", "authority", "perspective", "imply", "consequence", "debate", "theory"
    ]
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
        if "completed_topics" not in data: data["completed_topics"] = []
        if "next_lesson_prep" not in data: data["next_lesson_prep"] = None
        if "rotated_vocab" not in data: data["rotated_vocab"] = {"A2": [], "B1": [], "B2": []}
        if "lesson_history" not in data: data["lesson_history"] = []
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

# 🔥 YENİ: GPT İLE AKILLI KELİME SEÇİCİ
def get_relevant_vocab(client, topic, available_vocab_list):
    """
    Havuzdaki rastgele kelimeler yerine, GPT'ye sorup konuya uygun olanları seçtirir.
    """
    if len(available_vocab_list) <= 5:
        return available_vocab_list
    
    # Çok fazla kelimeyi GPT'ye göndermemek için 50 aday seçiyoruz
    candidates = random.sample(available_vocab_list, min(50, len(available_vocab_list)))
    
    prompt = f"""
    I have a lesson topic: "{topic}".
    I have a list of candidate words: {', '.join(candidates)}.
    
    TASK: Select exactly 5 words from the list that are MOST RELEVANT to the topic "{topic}".
    OUTPUT ONLY A JSON ARRAY of strings. Example: ["word1", "word2", "word3", "word4", "word5"]
    """
    
    try:
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        selected = strict_json_parse(res.choices[0].message.content)
        if isinstance(selected, list) and len(selected) > 0:
            return selected[:5] # En fazla 5 tane al
        else:
            return random.sample(candidates, 5) # Hata olursa rastgele dön
    except:
        return random.sample(candidates, 5) # Hata olursa rastgele dön

user_data = load_data()

# --- 4. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_minutes, speed_slow):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    # 1. Ödev Kontrolü
    assigned_topic = None
    assigned_vocab = []
    
    if mode == "LESSON" and user_data.get("next_lesson_prep"):
        plan = user_data["next_lesson_prep"]
        assigned_topic = plan.get("topic")
        assigned_vocab = plan.get("vocab", [])
        st.toast(f"📅 Planned Topic: {assigned_topic}", icon="check")

    # 2. Konu Seçimi
    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. TOPIC: {topic}. GOAL: Test user. RESPONSE STYLE: Short questions. ALWAYS ask a question."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions. ALWAYS ask a question."
    else:
        if assigned_topic:
            topic = assigned_topic
        else:
            all_topics = TOPIC_POOL.get(level, ["General"])
            completed = user_data.get("completed_topics", [])
            available_topics = [t for t in all_topics if t not in completed]
            if not available_topics:
                completed = [t for t in completed if t not in all_topics]
                user_data["completed_topics"] = completed
                save_data(user_data)
                available_topics = all_topics 
            topic = random.choice(available_topics)

        system_role = f"""
        ACT AS: Helpful English Coach. 
        LEVEL: {full_level_desc}. 
        TOPIC: {topic}. 
        RESPONSE STYLE: Keep answers UNDER 2 SENTENCES. 
        CRITICAL RULE: You MUST ALWAYS end your response with a related FOLLOW-UP QUESTION.
        """

    # 3. Kelime Seçimi (AKILLI + KONU ODAKLI)
    target_vocab = []
    review_vocab = []
    
    if mode == "LESSON":
        if assigned_vocab:
            target_vocab = assigned_vocab
        else:
            full_list = VOCAB_POOL.get(level, [])
            used_list = user_data["rotated_vocab"].get(level, [])
            
            # Havuzdan kullanılmayanları bul
            available_vocab = [w for w in full_list if w not in used_list]
            
            # Liste bitmişse sıfırla
            if len(available_vocab) < 5:
                user_data["rotated_vocab"][level] = [] 
                available_vocab = full_list
                save_data(user_data)
            
            # 🔥 BURASI DEĞİŞTİ: Rastgele değil, GPT ile konuya uygun seçiyoruz
            target_vocab = get_relevant_vocab(client, topic, available_vocab)

        # Spaced Repetition (Eski kelimelerden tekrar)
        learned_set = set(user_data.get("vocabulary_bank", []))
        if learned_set:
            past_candidates = [w for w in list(learned_set) if w not in target_vocab]
            if past_candidates:
                review_vocab = random.sample(past_candidates, min(3, len(past_candidates)))

    # State Başlatma
    st.session_state.lesson_active = True
    st.session_state.reading_phase = False 
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_minutes * 60 
    st.session_state.target_vocab = target_vocab
    st.session_state.review_vocab = review_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    st.session_state.speed_slow = speed_slow 
    
    vocab_instr = f"NEW WORDS: {', '.join(target_vocab)}. REVIEW WORDS: {', '.join(review_vocab)}."
    intro_instr = f"Start by saying 'Hello Pınar, how are you? Today we are going to talk about {topic}'."
    
    final_prompt = f"{system_role}\n{intro_instr}\nCONTEXT: {vocab_instr}\nIf user uses a target word, PRAISE briefly."
    st.session_state.messages = [{"role": "system", "content": final_prompt}]
    
    try:
        first_res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
        first_msg = first_res.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        tts = gTTS(text=first_msg, lang='en', slow=speed_slow)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        st.session_state.last_audio_response = audio_fp.getvalue()
        
        if mode == "LESSON" and user_data.get("next_lesson_prep"):
            user_data["next_lesson_prep"] = None
            save_data(user_data)
            
    except Exception as e:
        st.error(f"Başlatma hatası: {e}")
        st.session_state.lesson_active = False

# --- 5. ARAYÜZ ---
with st.sidebar:
    st.title("🎓 Pınar's Academy")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("API Key", type="password")

    st.divider()
    
    if st.button("📜 View Training History"):
        st.session_state.show_history = not st.session_state.get("show_history", False)

    st.divider()
    st.write("🔊 **Voice Speed**")
    speed_mode = st.radio("Select Speed:", ["Normal", "Slow (Tane Tane)"], horizontal=True)
    is_slow = True if "Slow" in speed_mode else False

    st.divider()
    sub = determine_sub_level(user_data['current_level'], user_data['lessons_completed'])
    c1, c2 = st.columns(2)
    with c1: st.metric("Level", f"{user_data['current_level']}")
    with c2: st.metric("Sub-Band", sub)
    
    st.caption(f"Completed Lessons: {user_data['lessons_completed']}")
    
    if user_data.get("next_lesson_prep"):
        st.info(f"📅 **Homework Topic:**\n{user_data['next_lesson_prep']['topic']}")

    if st.session_state.get("lesson_active", False):
        st.divider()
        st.success(f"**Topic:** {st.session_state.topic}")
        if st.session_state.target_vocab:
            st.markdown("**🆕 Target Words:**")
            st.write(", ".join(st.session_state.target_vocab))
            
        if not st.session_state.get("reading_phase", False):
            current_sec = st.session_state.accumulated_speaking_time
            target_sec = st.session_state.target_speaking_seconds
            prog = min(current_sec / target_sec, 1.0)
            curr_str = f"{int(current_sec // 60)}m {int(current_sec % 60)}s"
            targ_str = f"{int(target_sec // 60)}m {int(target_sec % 60)}s"
            st.progress(prog, text=f"Speaking Progress: {curr_str} / {targ_str}")

    st.divider()
    if st.button("RESET ALL DATA"):
        save_data({"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "rotated_vocab": {"A2": [], "B1": [], "B2": []}, "completed_topics": [], "lesson_history": [], "next_mode": "ASSESSMENT", "next_lesson_prep": None})
        st.rerun()

# --- 6. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    st.title("🗣️ AI Personal Coach (Blind Mode)")

    # --- GEÇMİŞ EKRANI ---
    if st.session_state.get("show_history", False):
        st.subheader("📜 Training History")
        history = user_data.get("lesson_history", [])
        if not history:
            st.info("No lesson history found yet.")
        else:
            for i, lesson in enumerate(reversed(history)):
                with st.expander(f"📚 {lesson.get('date', 'Date')} - {lesson.get('topic', 'Topic')}"):
                    st.write(f"**Score:** {lesson.get('score', 0)}")
                    st.write(f"**Words:** {', '.join(lesson.get('words', []))}")
                    st.write("**Feedback:**")
                    if 'feedback_pros' in lesson:
                        st.success("\n".join(lesson['feedback_pros']))
                    if 'feedback_cons' in lesson:
                        st.error("\n".join(lesson['feedback_cons']))
        
        if st.button("🔙 Back to Lessons"):
            st.session_state.show_history = False
            st.rerun()

    # --- NORMAL DERS EKRANI ---
    elif not st.session_state.get("lesson_active", False):
        st.markdown(f"### Welcome Pınar! Ready for **{user_data['current_level']}**?")
        
        if user_data.get("next_lesson_prep"):
            st.success(f"🎯 **Planned Lesson:** {user_data['next_lesson_prep']['topic']}")
            
        target_mins = st.slider("Target Speaking Time (Minutes)", 0.5, 30.0, 1.0, step=0.5)
        btn = "🚀 START LESSON" if user_data["next_mode"] != "EXAM" else "🔥 START EXAM"
        
        if st.button(btn, type="primary", use_container_width=True):
            with st.spinner("Preparing curriculum..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], target_mins, is_slow)
                st.rerun()

    else:
        # FAZ 1: KONUŞMA
        if not st.session_state.get("reading_phase", False):
            chat_container = st.container()
            with chat_container:
                messages_len = len(st.session_state.messages)
                for i, msg in enumerate(st.session_state.messages):
                    if msg["role"] != "system":
                        is_last_message = (i == messages_len - 1)
                        is_assistant = (msg["role"] == "assistant")

                        if is_last_message and is_assistant:
                            with st.chat_message("assistant", avatar="🤖"):
                                st.write("🔊 **Listening Mode...** (Play audio)")
                                with st.expander("👀 Click to reveal text"):
                                    st.write(msg["content"])
                        else:
                            avatar = "🤖" if msg["role"]=="assistant" else "👤"
                            with st.chat_message(msg["role"], avatar=avatar):
                                st.write(msg["content"])
            
            if "last_audio_response" in st.session_state and st.session_state.last_audio_response:
                st.audio(st.session_state.last_audio_response, format="audio/mp3", autoplay=True)

            st.write("---")
            c_mic, c_fin = st.columns([1, 4])
            
            with c_mic:
                audio = mic_recorder(start_prompt="🎤 SPEAK", stop_prompt="⏹️ SEND", key="recorder")
            
            with c_fin:
                current_spk = st.session_state.accumulated_speaking_time
                target_spk = st.session_state.target_speaking_seconds
                
                if st.button("➡️ GO TO WRITING/READING PART", use_container_width=True):
                    if user_data["next_mode"] != "ASSESSMENT" and current_spk < target_spk:
                        missing = target_spk - current_spk
                        st.toast(f"Keep speaking! {int(missing//60)}m {int(missing%60)}s left.", icon="⏳")
                    else:
                        st.session_state.reading_phase = True
                        with st.spinner("Generating reading task..."):
                            reading_prompt = f"""
                            Create a short reading passage (A2/B1 level appropriate) about: {st.session_state.topic}.
                            Then ask 3 comprehension questions.
                            OUTPUT JSON FORMAT:
                            {{
                                "text": "The passage text...",
                                "questions": ["Question 1", "Question 2", "Question 3"]
                            }}
                            """
                            try:
                                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": reading_prompt}])
                                content = strict_json_parse(res.choices[0].message.content)
                                st.session_state.reading_content = content
                            except:
                                st.session_state.reading_content = {"text": "Error.", "questions": ["Q1"]}
                        st.rerun()

            if audio:
                if "last_audio_bytes" not in st.session_state or audio['bytes'] != st.session_state.last_audio_bytes:
                    st.session_state.last_audio_bytes = audio['bytes']
                    with st.spinner("Processing..."):
                        try:
                            audio_bio = io.BytesIO(audio['bytes'])
                            audio_bio.name = "audio.webm"
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1", file=audio_bio, language="en", temperature=0.2,
                                prompt=f"The user is speaking English about {st.session_state.topic}."
                            ).text
                            
                            is_hallucination = False
                            for banned in BANNED_PHRASES:
                                if banned.lower() in transcript.lower():
                                    is_hallucination = True; break
                            
                            if is_hallucination or len(transcript.strip()) < 2:
                                st.warning("Audio unclear. Please try again.")
                            else:
                                word_count = len(transcript.split())
                                st.session_state.accumulated_speaking_time += word_count * 0.7
                                
                                st.session_state.messages.append({"role": "user", "content": transcript})
                                res = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages)
                                reply = res.choices[0].message.content
                                st.session_state.messages.append({"role": "assistant", "content": reply})
                                
                                tts = gTTS(text=reply, lang='en', slow=st.session_state.speed_slow)
                                audio_fp = io.BytesIO()
                                tts.write_to_fp(audio_fp)
                                st.session_state.last_audio_response = audio_fp.getvalue()
                                st.rerun()
                        except Exception as e: 
                            st.error(f"⚠️ AUDIO ERROR: {e}")

        # FAZ 2: YAZILI OKUMA SINAVI
        else:
            st.markdown("### 📖 Reading & Comprehension")
            content = st.session_state.get("reading_content", {})
            st.info(content.get("text", ""))
            st.write("---")
            
            with st.form("reading_quiz_form"):
                st.write("**Please answer the questions below (in English):**")
                answers = []
                questions = content.get("questions", [])
                for i, q in enumerate(questions):
                    ans = st.text_input(f"{i+1}. {q}", key=f"q_{i}")
                    answers.append(ans)
                submitted = st.form_submit_button("🏁 SUBMIT ANSWERS & GET FEEDBACK")
            
            if submitted:
                user_answers_dict = {f"Q{i+1}": ans for i, ans in enumerate(answers)}
                with st.spinner("Grading & Preparing Homework..."):
                    analysis_prompt = f"""
                    You are an English Teacher.
                    TASK 1: Analyze Speaking + Reading.
                    TASK 2: Check Reading Answers. If WRONG, provide CORRECT answer.
                    TASK 3: Prepare NEXT LESSON (Homework).
                    OUTPUT JSON:
                    {{
                        "score": (0-100),
                        "reading_feedback": [
                            {{"question": "Q1", "user_answer": "...", "correct_answer": "...", "is_correct": true/false}},
                            {{"question": "Q2", "user_answer": "...", "correct_answer": "...", "is_correct": true/false}},
                            {{"question": "Q3", "user_answer": "...", "correct_answer": "...", "is_correct": true/false}}
                        ],
                        "learned_words": [],
                        "pros": [], "cons": [], "suggestions": [],
                        "level_recommendation": "Stay/Up",
                        "next_lesson_homework": {{ "topic": "...", "vocab": ["..."] }}
                    }}
                    """
                    msgs = st.session_state.messages + [
                        {"role": "user", "content": f"Reading Answers: {json.dumps(user_answers_dict)}"},
                        {"role": "system", "content": analysis_prompt}
                    ]
                    try:
                        res = client.chat.completions.create(model="gpt-4o", messages=msgs)
                        rep = strict_json_parse(res.choices[0].message.content)
                        if not rep: rep = {"score": 75, "pros": [], "cons": [], "next_lesson_homework": {"topic": "General", "vocab": []}}

                        user_data["lessons_completed"] += 1
                        if st.session_state.topic not in user_data["completed_topics"]:
                            user_data["completed_topics"].append(st.session_state.topic)
                        
                        user_data["rotated_vocab"][user_data["current_level"]].extend(st.session_state.target_vocab)

                        if "learned_words" in rep: user_data["vocabulary_bank"].extend(rep["learned_words"])
                        if "next_lesson_homework" in rep: user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                        
                        if user_data["lessons_completed"] % 5 == 0: user_data["next_mode"] = "EXAM"
                        else: user_data["next_mode"] = "LESSON"
                        
                        # GEÇMİŞİ KAYDET
                        history_entry = {
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "topic": st.session_state.topic,
                            "score": rep.get("score"),
                            "words": st.session_state.target_vocab,
                            "feedback_pros": rep.get("pros", []),
                            "feedback_cons": rep.get("cons", [])
                        }
                        user_data["lesson_history"].append(history_entry)
                        
                        save_data(user_data)
                        
                        st.balloons()
                        st.markdown(f"## 📊 Final Score: {rep.get('score')}")
                        
                        st.subheader("📝 Reading Results")
                        for feedback in rep.get("reading_feedback", []):
                            color = "green" if feedback["is_correct"] else "red"
                            emoji = "✅" if feedback["is_correct"] else "❌"
                            with st.expander(f"{emoji} {feedback['question']}", expanded=True):
                                st.write(f"**You:** {feedback['user_answer']}")
                                if not feedback["is_correct"]:
                                    st.markdown(f":{color}[**Correct:** {feedback['correct_answer']}]")

                        st.divider()
                        c1, c2 = st.columns(2)
                        with c1: st.success(f"**✅ Pros:**\n" + "\n".join([f"- {i}" for i in rep.get('pros', [])]))
                        with c2: st.error(f"**🔻 Needs Work:**\n" + "\n".join([f"- {i}" for i in rep.get('cons', [])]))
                        
                        st.divider()
                        st.info(f"### 📅 NEXT LESSON HOMEWORK")
                        hw = rep.get("next_lesson_homework", {})
                        st.write(f"**Topic:** {hw.get('topic', 'General')}")
                        st.code(", ".join(hw.get('vocab', [])))

                        st.session_state.lesson_active = False
                        
                        if st.button("🚀 START NEXT LESSON NOW", type="primary", use_container_width=True):
                            st.session_state.messages = []
                            st.session_state.reading_phase = False
                            st.session_state.reading_content = {}
                            st.session_state.accumulated_speaking_time = 0
                            st.rerun()

                    except Exception as e:
                        st.error(f"Report Error: {e}")
                    
else:
    st.warning("Enter API Key")
