import streamlit as st
import requests
import json
import re
from typing import Dict, Any
import fitz

st.set_page_config(
    page_title="AI Interview Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar OpenAI key input
st.sidebar.title("Settings")
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

user_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=st.session_state.openai_api_key,
    type="password",
    help="If you want to use your own OpenAI key, paste it here. It will be sent to the backend for each request."
)
st.session_state.openai_api_key = user_key

API_BASE_URL = "https://ai-interview-copilot-backend.onrender.com"
def make_api_request(endpoint: str, files: Dict = None, data: Dict = None, api_key: str = None) -> Dict[str, Any]:
    try:
        url = f"{API_BASE_URL}{endpoint}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text}'
            raise Exception(error_msg)
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. The AI processing is taking longer than expected.")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to the backend server. Make sure it's running on port 8000.")
    except Exception as e:
        raise Exception(str(e))


def extract_text_from_file(uploaded_file) -> str:
    try:
        if uploaded_file.type == "application/pdf":
            pdf_bytes = uploaded_file.getvalue()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        elif uploaded_file.type in ["text/plain", "application/octet-stream"]:
            return uploaded_file.getvalue().decode("utf-8")
        else:
            return ""
    except Exception:
        return ""

def display_structured_questions(raw_text: str):
    sections = re.split(r"\n###\s*", raw_text)
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split('\n')
        section_title = lines[0].strip()
        questions = lines[1:]
        st.markdown(f"### {section_title}")
        for q in questions:
            q = q.strip()
            if not q:
                continue
            q = re.sub(r'^\d+\.\s*', '', q)
            st.markdown(f"- {q}")
        st.markdown("")

def ai_interview_assistant():
    st.title("🧠 AI Interview Assistant")
    st.markdown("---")
    st.markdown("""
    **Upload a candidate's resume and job description to get:**
    - 📋 Tailored candidate summary
    - ❓ Personalized interview questions (available on next page)
    - 🎯 Skills gap analysis
    """)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📄 Upload Resume")
        resume_file = st.file_uploader(
            "Choose resume file",
            type=["pdf", "txt"],
            help="Upload candidate's resume in PDF or TXT format"
        )
        if resume_file:
            st.success(f"✅ Uploaded: {resume_file.name}")

    with col2:
        st.subheader("📝 Job Description")
        job_description = st.text_area(
            "Enter the complete job description",
            height=200,
            placeholder="Paste the full job description here...",
            help="Include role requirements, skills, experience, and responsibilities"
        )
        if job_description:
            st.caption(f"Characters: {len(job_description)}")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_summary_btn = st.button(
            "🚀 Generate Summary",
            type="primary",
            use_container_width=True
        )

    if generate_summary_btn and resume_file and job_description.strip():
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            status_text.text("📤 Uploading resume and job description...")
            progress_bar.progress(20)

            files = {"resume": (resume_file.name, resume_file.getvalue())}
            data = {"job_description": job_description}

            status_text.text("🤖 AI is generating candidate summary...")
            progress_bar.progress(60)

            result = make_api_request("/generate-summary", files=files, data=data,api_key=st.session_state.get("openai_api_key"))

            progress_bar.progress(90)
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            summary = result.get("summary", "")
            st.markdown("### 🔍 Candidate Summary")
            st.info(summary)

            # Save for questions generation later
            st.session_state['resume_text'] = extract_text_from_file(resume_file)
            st.session_state['job_description'] = job_description
            st.session_state['summary'] = summary
            if len(summary) > 1000:
               st.success("✅ Summary generated and saved. Switch to 'Generate Questions' page for interview questions.")
            else:
               st.warning("⚠️ Summary is too short. Please check the resume and job description for completeness.")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")
            with st.expander("🔧 Troubleshooting"):
                st.markdown("""
                - Ensure backend server is running (`python backend/main.py`)
                - Check OpenAI API key
                - Resume must be text-readable (no scanned images)
                - Try shorter job description if too long
                """)

def generate_questions():
    st.title("🤖 Generate Questions")
    st.markdown("---")

    if 'resume_text' not in st.session_state or 'job_description' not in st.session_state:
        st.warning("Please generate summary first by uploading resume and job description in the 'AI Interview Assistant' page.")
        return

    interview_type = st.selectbox(
        "Select Interview Type",
        [
            "Technical",
            "HR/Behavioral",
            "Managerial/Leadership",
            "Cultural Fit",
            "Case Study/Problem Solving",
            "Industry-Specific"
        ],
        help="Choose the type of interview for question tailoring"
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_questions_btn = st.button(
            "🚀 Generate Questions",
            type="primary",
            use_container_width=True
        )

    if generate_questions_btn:
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            status_text.text("🤖 AI is generating interview questions...")
            progress_bar.progress(50)
            data = {
                "resume_text": st.session_state['resume_text'],
                "job_description": st.session_state['job_description'],
                "interview_type": interview_type
            }
            result = make_api_request("/generate-questions", data=data,api_key=st.session_state.get("openai_api_key"))
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            questions_raw = "\n".join(result.get("questions", []))
            st.markdown(f"### ❓ Suggested {interview_type} Interview Questions")
            display_structured_questions(questions_raw)
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Generate summary", "Generate Questions"])

    if page == "Generate summary":
        ai_interview_assistant()
    else:
        generate_questions()

    # Footer same style as your example
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Made with ❤️ for better hiring decisions"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
