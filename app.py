import streamlit as st
from utils import *
from openai import OpenAI

st.set_page_config(
    page_title="AI Interview Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("Settings")
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

user_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=st.session_state.openai_api_key,
    type="password",
    help="If you want to use your own OpenAI key, paste it here."
)
st.session_state.openai_api_key = user_key


def generate_summary():
    st.title("🧠 AI Interview Assistant")
    st.markdown("---")
    st.markdown("""
    Upload a candidate's resume and job description to get:
    - 📋 Tailored candidate summary
    - ❓ Personalized interview questions
    - 🎯 Skills gap analysis
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Upload Resume")
        resume_file = st.file_uploader("Choose resume file", type=["pdf", "txt"])
        if resume_file:
            st.success(f"✅ Uploaded: {resume_file.name}")

    with col2:
        st.subheader("📝 Job Description")
        job_description = st.text_area("Paste job description here...", height=105)
        if job_description:
            st.caption(f"Characters: {len(job_description)}")

    st.markdown("---")
    if st.button("🚀 Generate Summary", type="primary",use_container_width=True) and resume_file and job_description.strip():
        status_text, progress_bar = show_progress("📤 Uploading files...", 20)

        try:
            files = {"resume": (resume_file.name, resume_file.getvalue())}
            data = {"job_description": job_description}
            status_text.text("🤖 AI is generating candidate summary...")
            progress_bar.progress(60)

            result = make_api_request("/generate-summary", files=files, data=data, api_key=st.session_state.openai_api_key)

            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            summary = result.get("summary", "")
            st.markdown("### 🔍 Candidate Summary")
            st.info(summary)

            st.session_state.update({
                'resume_text': extract_text_from_file(resume_file),
                'job_description': job_description,
                'summary': summary
            })

            if len(summary) > 1000:
                st.success("✅ Summary generated. Switch to 'Generate Questions' page.")
            else:
                st.warning("⚠️ Summary is short. Check resume and job description.")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")

def generate_questions():
    st.title("🤖 Generate Questions")
    st.markdown("---")

    if not all(k in st.session_state for k in ['resume_text', 'job_description']):
        st.warning("Please generate summary first.")
        return
    interview_types = load_interview_types()
    interview_type = st.selectbox("Select Interview Type", interview_types)

    if st.button("🚀 Generate Questions", type="primary"):
        status_text, progress_bar = show_progress("🤖 AI is generating questions...", 50)
        try:
            data = {
                "resume_text": st.session_state['resume_text'],
                "job_description": st.session_state['job_description'],
                "interview_type": interview_type
            }
            result = make_api_request("/generate-questions", data=data, api_key=st.session_state.openai_api_key)

            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            questions_raw = "\n".join(result.get("questions", []))
            st.session_state["questions"] = questions_raw.split('\n')
            st.markdown(f"### ❓ Suggested {interview_type} Interview Questions")
            display_structured_questions(questions_raw)
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")

def ai_interview():
    st.title("🎤 AI Voice Interview")

    if not st.session_state.openai_api_key:
        st.error("⚠ Please enter your OpenAI API key in the sidebar.")
        return

    # Ensure questions are available
    if "questions" not in st.session_state or not st.session_state["questions"]:
        st.warning("⚠ Please generate interview questions first.")
        return

    client = OpenAI(api_key=st.session_state.openai_api_key)

    # Session state vars
    if "current_q" not in st.session_state:
        st.session_state.current_q = 0
    if "transcripts" not in st.session_state:
        st.session_state.transcripts = []
    if st.session_state.current_q < len(st.session_state["questions"]):
        question = st.session_state["questions"][st.session_state.current_q]
        q_num = st.session_state.current_q + 1 

        if st.button(f"▶ Start Question {q_num}", use_container_width=True):
            speak_tts(client, question)

        audio_input = st.audio_input("🎙 Your Answer")

        if audio_input and st.button("💬 Submit Answer", use_container_width=True):
            answer_text = transcribe_audio(client, audio_input)
            st.session_state.transcripts.append({
                "question": question,
                "answer": answer_text
            })
            save_transcript_to_file(question, answer_text)
            st.session_state.current_q += 1
            st.rerun()

    else:
        st.success("✅ Interview complete!")
        clear_transcript_file()
        

    if st.session_state.transcripts:
        st.subheader("📜 Interview Transcript")
        for idx, item in enumerate(st.session_state.transcripts, 1):
            st.write(f"**Q {idx}:** {item['question']}")
            st.write(f"**A {idx}:** {item['answer']}")


def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Generate summary", "Generate Questions","AI Interview"])
    if page == "Generate summary":
        generate_summary()
    elif page == "Generate Questions":
        generate_questions()
    else:
         ai_interview()

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>Made with ❤️ for better hiring decisions</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()