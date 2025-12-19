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
st.set_page_config(page_title="Pınar's Friend v7 (Blind Mode)", page_icon="🎧", layout="wide")
DATA_FILE = "user_data.json"

# --- HALÜSİNASYON FİLTRESİ ---
BANNED_PHRASES = [
    "Hi, how are you?", "Good to see you", "Thank you", "Thanks for watching", 
    "Copyright", "Subscribe", "Amara.org", "Watch this video", "You", 
    "I could not think of anything", "Silence", "Bye"
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
        return {
            "current_level": "A2", 
            "lessons_completed": 0, 
            "exam_scores": [], 
            "vocabulary_bank": [], 
            "next_mode": "ASSESSMENT",
            "next_lesson_prep": None 
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        if "next_lesson_prep" not in data: data["next_lesson_prep"] = None
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

user_data = load_data()

# --- 3. DERS MANTIĞI ---
def start_lesson_logic(client, level, mode, target_speaking_seconds):
    sub_level = determine_sub_level(level, user_data["lessons_completed"])
    full_level_desc = f"{level} ({sub_level})"
    
    assigned_topic = None
    assigned_vocab = []
    
    if mode == "LESSON" and user_data.get("next_lesson_prep"):
        plan = user_data["next_lesson_prep"]
        assigned_topic = plan.get("topic")
        assigned_vocab = plan.get("vocab", [])
        user_data["next_lesson_prep"] = None 
        save_data(user_data)
        st.toast(f"📅 Planned Lesson Loaded: {assigned_topic}", icon="check")

    if mode == "EXAM":
        topic = random.choice(TOPIC_POOL[level])
        system_role = f"ACT AS: Strict Examiner. LEVEL: {full_level_desc}. TOPIC: {topic}. GOAL: Test user. RESPONSE STYLE: Short questions."
    elif mode == "ASSESSMENT":
        topic = "Level Assessment"
        system_role = "ACT AS: Examiner. GOAL: Determine level. Ask 3 questions."
    else:
        topic = assigned_topic if assigned_topic else random.choice(TOPIC_POOL.get(level, ["General"]))
        system_role = f"ACT AS: Helpful Coach. LEVEL: {full_level_desc}. TOPIC: {topic}. RESPONSE STYLE: Keep answers UNDER 2 SENTENCES."

    target_vocab = []
    review_vocab = []
    
    if mode == "LESSON":
        if assigned_vocab:
            target_vocab = assigned_vocab
        else:
            full_vocab_list = ["happy", "travel", "friend", "time", "weather", "family", "weekend", "food", "city", "music"]
            if level == "B1": full_vocab_list = ["opinion", "suggest", "experience", "prefer", "describe", "recently", "challenge", "career", "habit", "culture"]
            elif level == "B2": full_vocab_list = ["perspective", "imply", "consequence", "debate", "theory", "significant", "approach", "justify", "complex", "adapt"]

            learned_set = set(user_data.get("vocabulary_bank", []))
            unknown_words = [w for w in full_vocab_list if w not in learned_set]
            pool = unknown_words if len(unknown_words) >= 5 else full_vocab_list
            target_vocab = random.sample(pool, min(5, len(pool)))

        learned_set = set(user_data.get("vocabulary_bank", []))
        if learned_set:
            past_candidates = [w for w in list(learned_set) if w not in target_vocab]
            if past_candidates:
                review_vocab = random.sample(past_candidates, min(3, len(past_candidates)))

    st.session_state.lesson_active = True
    st.session_state.reading_phase = False 
    st.session_state.accumulated_speaking_time = 0.0 
    st.session_state.target_speaking_seconds = target_speaking_seconds
    st.session_state.target_vocab = target_vocab
    st.session_state.review_vocab = review_vocab
    st.session_state.topic = topic
    st.session_state.last_audio_bytes = None
    
    vocab_instr = f"NEW WORDS: {', '.join(target_vocab)}. REVIEW WORDS: {', '.join(review_vocab)}."
    intro_instr = f"Start by saying 'Hello Pınar, how are you? Today we are going to talk about {topic}'."
    
    final_prompt = f"{system_role}\n{intro_instr}\nCONTEXT: {vocab_instr}\nIf user uses a target word, PRAISE briefly."
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
    st.title("🎓 Pınar's Academy")
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("API Key", type="password")

    st.divider()
    sub = determine_sub_level(user_data['current_level'], user_data['lessons_completed'])
    c1, c2 = st.columns(2)
    with c1: st.metric("Level", f"{user_data['current_level']}")
    with c2: st.metric("Sub-Band", sub)
    
    st.caption(f"Completed Lessons: {user_data['lessons_completed']}")
    
    if user_data.get("next_lesson_prep"):
        st.info(f"📅 **Next Lesson Plan:**\nTopic: {user_data['next_lesson_prep']['topic']}")

    if st.session_state.get("lesson_active", False):
        st.divider()
        st.success(f"**Topic:** {st.session_state.topic}")
        
        if st.session_state.target_vocab:
            st.markdown("**🆕 Target Words:**")
            st.write(", ".join(st.session_state.target_vocab))
            
        if st.session_state.get("review_vocab"):
            st.markdown("**🔄 Review These:**")
            st.write(", ".join(st.session_state.review_vocab))
            
        if not st.session_state.get("reading_phase", False):
            current = st.session_state.accumulated_speaking_time
            target = st.session_state.target_speaking_seconds
            prog = min(current / target, 1.0)
            st.progress(prog, text=f"Speaking: {int(current)}/{int(target)}s")

    st.divider()
    if st.button("RESET ALL DATA"):
        save_data({"current_level": "A2", "lessons_completed": 0, "exam_scores": [], "vocabulary_bank": [], "next_mode": "ASSESSMENT", "next_lesson_prep": None})
        st.rerun()

# --- 5. ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    st.title("🗣️ AI Personal Coach (Blind Mode)")

    if not st.session_state.get("lesson_active", False):
        st.markdown(f"### Welcome Pınar! Ready for **{user_data['current_level']}**?")
        target_sec = st.slider("Target Speaking Time (Seconds)", 30, 300, 60, step=30)
        btn = "🚀 START LESSON" if user_data["next_mode"] != "EXAM" else "🔥 START EXAM"
        if st.button(btn, type="primary", use_container_width=True):
            with st.spinner("Preparing curriculum..."):
                start_lesson_logic(client, user_data["current_level"], user_data["next_mode"], target_sec)
                st.rerun()

    else:
        # FAZ 1: KONUŞMA (BLIND LISTENING MODE)
        if not st.session_state.get("reading_phase", False):
            
            # --- 🔥 BLIND MODE GÖSTERİM MANTIĞI ---
            # Mesajları döngüye sokuyoruz.
            # Eğer mesaj "Assistant"ın SON mesajı ise -> GİZLE.
            # Değilse -> GÖSTER.
            
            chat_container = st.container()
            with chat_container:
                messages_len = len(st.session_state.messages)
                for i, msg in enumerate(st.session_state.messages):
                    if msg["role"] != "system":
                        is_last_message = (i == messages_len - 1)
                        is_assistant = (msg["role"] == "assistant")

                        # Eğer son mesaj asistanınsa -> GİZLE (Kör Modu)
                        if is_last_message and is_assistant:
                            with st.chat_message("assistant", avatar="🤖"):
                                st.write("🔊 **Dinleme Modu Aktif...** (Cevabı duymak için oynatın)")
                                with st.expander("👀 Duyduğunu anlayamadın mı? Metni görmek için tıkla."):
                                    st.write(msg["content"])
                        
                        # Diğer tüm mesajları normal göster
                        else:
                            avatar = "🤖" if msg["role"]=="assistant" else "👤"
                            with st.chat_message(msg["role"], avatar=avatar):
                                st.write(msg["content"])
            
            # Ses Oynatıcı (Metnin altında)
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
                        st.toast("Not enough speaking time!", icon="🚫")
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
                                
                                tts = gTTS(text=reply, lang='en')
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
                submitted = st.form_submit_button("🏁 SUBMIT ANSWERS & FINISH LESSON")
            
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
                        if "learned_words" in rep: user_data["vocabulary_bank"].extend(rep["learned_words"])
                        if "next_lesson_homework" in rep: user_data["next_lesson_prep"] = rep["next_lesson_homework"]
                        
                        if user_data["lessons_completed"] % 5 == 0: user_data["next_mode"] = "EXAM"
                        else: user_data["next_mode"] = "LESSON"
                        
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

                    except Exception as e:
                        st.error(f"Report Error: {e}")
                    
else:
    st.warning("Enter API Key")
