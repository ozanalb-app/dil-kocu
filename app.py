import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import streamlit.components.v1 as components
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Dil Koçu (Whisper)", page_icon="🎧")

st.title("🎧 Pro Dil Koçu (Yüksek Kalite)")
st.info("Bu mod OpenAI Whisper kullanır. Aksanınızı ve hatalarınızı çok daha iyi anlar.")

# --- AYARLAR ---
with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")
    dil = st.radio("Dil Seçimi", ["İngilizce", "Türkçe"])
    lang_code = "en" if dil == "İngilizce" else "tr"

# --- TTS (SESLENDİRME) ---
def speak(text, lang):
    js = f"""
    <script>
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance("{text.replace('"', '')}");
        msg.lang = "{'en-US' if lang == 'en' else 'tr-TR'}";
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js, height=0)

# --- ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # SOHBETİ GÖSTER
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # --- MİKROFON (KAYIT ALIP GÖNDERME) ---
    st.write("---")
    st.write("Mikrofona basın, konuşun ve durdurun:")
    
    # Sesi dosya olarak alıyoruz (Bytes)
    audio = mic_recorder(
        start_prompt="🔴 Kaydı Başlat",
        stop_prompt="⏹️ Bitir ve Gönder",
        key="recorder"
    )

    if audio:
        # Sesi OpenAI Whisper'a gönderiyoruz
        with st.spinner("Sesiniz analiz ediliyor (Whisper)..."):
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = "audio.webm"
            
            # KÜÇÜK AMA ETKİLİ DOKUNUŞ: 'prompt' parametresini ekledik.
            # Modele "Bu bir dil öğrenme seansı" diyerek ipucu veriyoruz.
            context_prompt = "This is a language learning session. The user might have an accent."
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_bio,
                language=lang_code,
                prompt=context_prompt 
            )
            user_text = transcript.text

        # Eğer yeni bir şey söylediyse işle
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != user_text:
            
            # Kullanıcı mesajı
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.write(user_text)

            # GPT Cevabı
            with st.chat_message("assistant"):
                with st.spinner("Cevap hazırlanıyor..."):
                    system_msg = f"Sen {dil} öğreten, B1 seviyesinde konuşan sabırlı bir öğretmensin. Hataları düzelt."
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_msg}] + st.session_state.messages
                    )
                    reply = response.choices[0].message.content
                    
                    st.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    
                    # Seslendir
                    speak(reply, lang_code)

else:
    st.warning("Lütfen API anahtarını girin.")