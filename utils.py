import streamlit as st
import requests
import re
import fitz
from typing import Dict, Any
from config import API_BASE_URL, INTERVIEW_TYPES_FILE, TRANSCRIPT_FILE
import io
from openai import OpenAI

def make_api_request(endpoint: str, files: Dict = None, data: Dict = None, api_key: str = None) -> Dict[str, Any]:
    """Generic API request handler."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text}'
            raise Exception(error_msg)
    except requests.exceptions.Timeout:
        raise Exception("Request timed out.")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to the backend server.")
    except Exception as e:
        raise Exception(str(e))

def extract_text_from_file(uploaded_file) -> str:
    """Extract text from PDF or TXT."""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_bytes = uploaded_file.getvalue()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return "".join(page.get_text() for page in doc)
        elif uploaded_file.type in ["text/plain", "application/octet-stream"]:
            return uploaded_file.getvalue().decode("utf-8")
        return ""
    except Exception:
        return ""

def load_interview_types(file_path=INTERVIEW_TYPES_FILE):
    """Read interview types from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        st.error(f"Interview type file not found: {file_path}")
        return []

def display_structured_questions(raw_text: str):
    """Display AI-generated questions without headings."""
    lines = raw_text.strip().split('\n')
    for q in lines:
        q = re.sub(r'^\d+\.\s*', '', q.strip())  # remove numbering if present
        if q:
            st.markdown(f"- {q}")


def show_progress(message, progress):
    """Helper to show progress bar."""
    status_text = st.empty()
    status_text.text(message)
    progress_bar = st.progress(progress)
    return status_text, progress_bar

def speak_tts(client, text):
    """Speak text using GPT-4o-mini-TTS directly in memory."""
    audio_buffer = io.BytesIO()
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=text,
        instructions="Speak in a professional and clear tone."
    ) as response:
        for chunk in response.iter_bytes():
            audio_buffer.write(chunk)

    audio_buffer.seek(0)
    st.audio(audio_buffer, format="audio/mp3")


def transcribe_audio(client, audio_file):
    """Transcribe recorded audio to text."""
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcription.text

def save_transcript_to_file(question, answer):
    """Append question and answer to a text file."""
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
        f.write(f"Q: {question}\n")
        f.write(f"A: {answer}\n\n")
        
def clear_transcript_file():
    """Clear the transcript file."""
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("")