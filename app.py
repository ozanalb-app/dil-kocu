import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Dil Koçu", page_icon="🎧")

st.title("🎧 Pro Dil Koçu")
st.markdown("Whisper (Kulak) + GPT-4o (Beyin) + Onyx (Ses)")

# --- AYARLAR ---
with st.sidebar:
    # Eğer secrets'ta şifre varsa onu al, yoksa kutucuk göster
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    dil = st.radio("Dil Seçimi", ["İngilizce", "Türkçe"])
    lang_code = "en" if dil == "İngilizce" else "tr"

# --- ANA AKIŞ ---
if api_key:
    client = OpenAI(api_key=api_key)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # SOHBETİ GÖSTER
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # --- MİKROFON ---
    st.write("---")
    st.write("Mikrofona basın, konuşun ve durdurun:")
    
    # Sesi al
    audio = mic_recorder(
        start_prompt="🎤 Kaydı Başlat",
        stop_prompt="⏹️ Bitir ve Gönder",
        key="recorder"
    )

    if audio:
        # 1. WHISPER (Sesi Yazıya Çevir)
        with st.spinner("Sesiniz analiz ediliyor..."):
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = "audio.webm"
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_bio,
                language=lang_code
            )
            user_text = transcript.text

        # Yeni bir şey söylendiyse işle
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != user_text:
            
            # Kullanıcı mesajını ekrana yaz
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.write(user_text)

            # 2. GPT (Cevap Üret)
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

                    # 3. TTS (Sesi Oku - MP3 Olarak)
                    # OpenAI'ın kendi ses motorunu kullanıyoruz.
                    # Ses seçenekleri: alloy, echo, fable, onyx, nova, shimmer
                    tts_response = client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=reply
                    )
                    
                    # Ekrana bir ses oynatıcı koy ve otomatik başlat
                    st.audio(tts_response.content, format="audio/mp3", autoplay=True)

else:
    st.warning("Lütfen API anahtarını girin.")
