import streamlit as st
import requests
import re
import fitz  # PyMuPDF for PDF text extraction
from typing import Dict, Any
from config import API_BASE_URL, INTERVIEW_TYPES_FILE, TRANSCRIPT_FILE
import io
from openai import OpenAI
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import os

# Function to make API requests to the backend
def make_api_request(endpoint: str, files: Dict = None, data: Dict = None, api_key: str = None) -> Dict[str, Any]:
    """Generic API request handler."""
    try:
        url = f"{API_BASE_URL}{endpoint}"  # Construct the full API URL
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()  # Return JSON response if successful
        else:
            # Handle errors and extract error messages
            try:
                error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text}'
            raise Exception(error_msg)
    except requests.exceptions.Timeout:
        raise Exception("Request timed out.")  # Handle timeout errors
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to the backend server.")  # Handle connection errors
    except Exception as e:
        raise Exception(str(e))  # Handle other exceptions

# Function to extract text from uploaded files (PDF or TXT)
def extract_text_from_file(uploaded_file) -> str:
    """Extract text from PDF or TXT."""
    try:
        if uploaded_file.type == "application/pdf":
            # Extract text from PDF using PyMuPDF
            pdf_bytes = uploaded_file.getvalue()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return "".join(page.get_text() for page in doc)  # Concatenate text from all pages
        elif uploaded_file.type in ["text/plain", "application/octet-stream"]:
            # Extract text from plain text files
            return uploaded_file.getvalue().decode("utf-8")
        return ""
    except Exception:
        return ""  # Return empty string if extraction fails

# Function to load interview types from a file
def load_interview_types(file_path=INTERVIEW_TYPES_FILE):
    """Read interview types from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]  
    except FileNotFoundError:
        st.error(f"Interview type file not found: {file_path}")
        return []

# Function to display AI-generated questions in a structured format
def display_structured_questions(raw_text: str):
    """Display AI-generated questions without headings."""
    lines = raw_text.strip().split('\n')  # Split text into lines
    for q in lines:
        q = re.sub(r'^\d+\.\s*', '', q.strip())  # Remove numbering if present
        if q:
            st.markdown(f"- {q}")  # Display each question as a bullet point

# Function to show a progress bar with a message
def show_progress(message, progress):
    """Helper to show progress bar."""
    status_text = st.empty()  # Create an empty placeholder for the status text
    status_text.text(message)  # Display the message
    progress_bar = st.progress(progress)  # Display the progress bar
    return status_text, progress_bar

# Function to use text-to-speech (TTS) to speak text
def speak_tts(client, text):
    """Speak text using GPT-4o-mini-TTS directly in memory."""
    audio_buffer = io.BytesIO()  # Create an in-memory buffer for audio
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",  # Specify the TTS model
        voice="coral",  # Specify the voice
        input=text,  # Input text to be spoken
        instructions="Speak in a professional and clear tone."  # Instructions for the voice
    ) as response:
        for chunk in response.iter_bytes():
            audio_buffer.write(chunk)  # Write audio chunks to the buffer

    audio_buffer.seek(0)  # Reset the buffer pointer to the beginning
    st.audio(audio_buffer, format="audio/mp3")  # Play the audio in Streamlit

# Function to transcribe audio to text using OpenAI's Whisper model
def transcribe_audio(client, audio_file):
    """Transcribe recorded audio to text."""
    transcription = client.audio.transcriptions.create(
        model="whisper-1",  # Specify the transcription model
        file=audio_file  # Input audio file
    )
    return transcription.text  # Return the transcribed text

# Function to save a question and answer pair to a transcript file
def save_transcript_to_file(question, answer):
    """Append question and answer to a text file."""
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
        f.write(f"Q: {question}\n")  # Write the question
        f.write(f"A: {answer}\n\n")  # Write the answer

# Function to clear the transcript file
def clear_transcript_file():
    """Clear the transcript file."""
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("")  # Overwrite the file with an empty string
        
# Function to evaluate the answer 
def evaluate_answer(file_path: str, api_key: str | None = None):
    """
    Creates an LLM chain for evaluating a candidate's answers from an interview transcript.
    Returns the LLMChain object so you can call .run({"transcript": ...}) elsewhere.
    """
    # Read transcript
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Transcript file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read().strip()
    
    if not transcript_text:
        raise ValueError("Interview transcript is empty.")
    
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise Exception("OPENAI_API_KEY not found. Provide it via env or pass api_key.")
    
    prompt_template = """
You are a highly experienced hiring manager and interview panel lead with deep expertise in candidate assessment.
Your task is to evaluate the candidate's answers in the transcript and provide a structured, evidence-based verdict.

### Evaluation Framework
1. **Understanding & Relevance** — Did the candidate understand the question and provide relevant answers?
2. **Depth of Knowledge** — Did the answers demonstrate expertise, technical depth, and real-world experience?
3. **Clarity & Communication** — Were responses clear, structured, and easy to follow?
4. **Problem-Solving & Critical Thinking** — Did the candidate show analytical thinking, creativity, and logical reasoning?
5. **Behavioral & Soft Skills** — Were responses aligned with good teamwork, leadership, adaptability, and culture fit?
6. **Examples & Evidence** — Did the candidate support answers with concrete examples and measurable achievements?
7. **Overall Impression** — Did the performance match, exceed, or fall short of expectations for this role?

---

### Interview Transcript:
{transcript}

---

### Output Format:
## Candidate Answer Evaluation Report

### Strengths
[List 2-5 strengths with supporting examples from the transcript]

### Areas for Improvement
[List 2-5 improvement areas with reasoning]

### Verdict
**Fit Score**: [X/10] — Explanation of score  
**Recommendation**:
- [ ] Strong Yes — Exceptional fit  
- [ ] Yes — Good fit  
- [ ] Maybe — Mixed performance, further assessment needed  
- [ ] No — Not a good fit for this role  
- [ ] Strong No — Clear mismatch

Be objective, evidence-based, and base all reasoning strictly on the transcript provided.
"""
    prompt = PromptTemplate(input_variables=["transcript"], template=prompt_template)
    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini", openai_api_key=key)
    chain = LLMChain(llm=llm, prompt=prompt, verbose=True)
    return chain
