import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import streamlit.components.v1 as components
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dil Koçu (Eco Mod)", page_icon="🌱")

st.title("🌱 Dil Koçu (Ekonomik Mod)")
st.markdown("**Kulak:** Whisper (Mükemmel) | **Ses:** Tarayıcı (Bedava)")

# --- AYARLAR ---
with st.sidebar:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    dil = st.radio("Dil Seçimi", ["İngilizce", "Türkçe"])
    lang_code = "en" if dil == "İngilizce" else "tr"

# --- BEDAVA SES MOTORU (JS) ---
def speak(text, lang):
    # JavaScript ile tarayıcıyı konuşturuyoruz (Bedava)
    js = f"""
    <script>
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance("{text.replace('"', '')}");
        msg.lang = "{'en-US' if lang == 'en' else 'tr-TR'}";
        // Ses hızını ayarlayabilirsin (1.0 normal, 0.9 biraz yavaş)
        msg.rate = 0.9; 
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js, height=0)

# --- ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sohbeti Göster
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # --- MİKROFON (WHISPER KALİTESİ) ---
    st.write("---")
    st.write("Mikrofona basın, konuşun ve durdurun:")
    
    audio = mic_recorder(
        start_prompt="🔴 Kaydı Başlat",
        stop_prompt="⏹️ Bitir ve Gönder",
        key="recorder"
    )

    if audio:
        # 1. WHISPER (Seni Mükemmel Anlar - Ücretli ama Ucuz)
        with st.spinner("Whisper ile dinleniyor..."):
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = "audio.webm"
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_bio,
                language=lang_code
            )
            user_text = transcript.text

        # Yeni mesaj varsa işle
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != user_text:
            
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.write(user_text)

            # 2. GPT (Cevap Verir - Ücretli ama Ucuz)
            with st.chat_message("assistant"):
                with st.spinner("Cevap hazırlanıyor..."):
                    system_msg = f"Sen {dil} öğreten yardımsever bir öğretmensin. Kısa ve net cevap ver."
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_msg}] + st.session_state.messages
                    )
                    reply = response.choices[0].message.content
                    
                    st.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    
                    # 3. TARAYICI SESİ (Bedava)
                    speak(reply, lang_code)

else:
    st.warning("Lütfen API anahtarını girin.")
