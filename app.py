import streamlit as st
from utils import *
from openai import OpenAI
from config import TRANSCRIPT_FILE

# Set up the Streamlit page configuration
st.set_page_config(
    page_title="AI Interview Assistant",  # Title of the app
    page_icon="🧠",  # Icon for the app
    layout="wide",  # Use a wide layout
    initial_sidebar_state="expanded"  # Sidebar starts expanded
)

# Sidebar settings for OpenAI API key input
st.sidebar.title("Settings")
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""  # Initialize OpenAI API key in session state

# Input field for OpenAI API key in the sidebar
user_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=st.session_state.openai_api_key,
    type="password",  # Mask the input for security
    help="If you want to use your own OpenAI key, paste it here."
)
st.session_state.openai_api_key = user_key  # Store the key in session state

# Function to generate a summary from a resume and job description
def generate_summary():
    st.title("🧠 AI Interview Assistant")  # App title
    st.markdown("---")  # Horizontal line
    st.markdown("""
    Upload a candidate's resume and job description to get:
    - 📋 Tailored candidate summary
    - ❓ Personalized interview questions
    - 🎯 Skills gap analysis
    """)

    # Create two columns for resume upload and job description input
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Upload Resume")  # Section for uploading resume
        resume_file = st.file_uploader("Choose resume file", type=["pdf", "txt"])  # File uploader
        if resume_file:
            st.success(f"✅ Uploaded: {resume_file.name}")  # Display success message

    with col2:
        st.subheader("📝 Job Description")  # Section for job description input
        job_description = st.text_area("Paste job description here...", height=105)  # Text area for input
        if job_description:
            st.caption(f"Characters: {len(job_description)}")  # Display character count

    st.markdown("---")  # Horizontal line
    # Button to trigger summary generation
    if st.button("🚀 Generate Summary", type="primary", use_container_width=True) and resume_file and job_description.strip():
        status_text, progress_bar = show_progress("📤 Uploading files...", 20)  # Show progress bar

        try:
            # Prepare data for API request
            files = {"resume": (resume_file.name, resume_file.getvalue())}
            data = {"job_description": job_description}
            status_text.text("🤖 AI is generating candidate summary...")
            progress_bar.progress(60)

            # Make API request to generate summary
            result = make_api_request("/generate-summary", files=files, data=data, api_key=st.session_state.openai_api_key)

            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            # Display the generated summary
            summary = result.get("summary", "")
            st.markdown("### 🔍 Candidate Summary")
            st.info(summary)

            # Store data in session state for later use
            st.session_state.update({
                'resume_text': extract_text_from_file(resume_file),
                'job_description': job_description,
                'summary': summary
            })

            # Provide feedback on the summary length
            if len(summary) > 1000:
                st.success("✅ Summary generated. Switch to 'Generate Questions' page.")
            else:
                st.warning("⚠️ Summary is short. Check resume and job description.")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")  # Display error message

# Function to generate interview questions
def generate_questions():
    st.title("🤖 Generate Questions")  # Page title
    st.markdown("---")  # Horizontal line

    # Check if summary data is available in session state
    if not all(k in st.session_state for k in ['resume_text', 'job_description']):
        st.warning("Please generate summary first.")  # Warn user if summary is missing
        return

    # Load interview types and display a dropdown for selection
    interview_types = load_interview_types()
    interview_type = st.selectbox("Select Interview Type", interview_types)

    # Button to trigger question generation
    if st.button("🚀 Generate Questions", type="primary"):
        status_text, progress_bar = show_progress("🤖 AI is generating questions...", 50)  # Show progress bar
        try:
            # Prepare data for API request
            data = {
                "resume_text": st.session_state['resume_text'],
                "job_description": st.session_state['job_description'],
                "interview_type": interview_type
            }
            # Make API request to generate questions
            result = make_api_request("/generate-questions", data=data, api_key=st.session_state.openai_api_key)

            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            # Display the generated questions
            questions_raw = "\n".join(result.get("questions", []))
            st.session_state["questions"] = questions_raw.split('\n')
            st.markdown(f"### ❓ Suggested {interview_type} Interview Questions")
            display_structured_questions(questions_raw)
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")  # Display error message

# Function to conduct an AI-powered voice interview
def ai_interview():
    st.title("🎤 AI Voice Interview")  # Page title
    
    # Check if OpenAI API key is provided
    if not st.session_state.openai_api_key:
        st.error("⚠ Please enter your OpenAI API key in the sidebar.")
        return

    # Ensure questions are available
    if "questions" not in st.session_state or not st.session_state["questions"]:
        st.warning("⚠ Please generate interview questions first.")
        return

    # Let user select number of questions (default 5 or max available)
    num_questions = st.number_input(
        "📋 Number of Questions for Interview",
        min_value=1,
        max_value=len(st.session_state["questions"]),
        value=st.session_state.get("num_questions", min(5, len(st.session_state["questions"]))),
        step=1
    )

    st.session_state.num_questions = num_questions
    st.info(f"✅ The interview will have {num_questions} questions.")

    # Limit questions list dynamically
    st.session_state.questions = st.session_state.questions[:num_questions]

    client = OpenAI(api_key=st.session_state.openai_api_key)  # Initialize OpenAI client

    # Initialize progress tracking
    if "current_q" not in st.session_state:
        st.session_state.current_q = 0
    if "transcripts" not in st.session_state:
        st.session_state.transcripts = []

    # Interview in progress
    if st.session_state.current_q < st.session_state.num_questions:
        question = st.session_state["questions"][st.session_state.current_q]
        q_num = st.session_state.current_q + 1 

        if st.button(f"▶ Start Question {q_num}", use_container_width=True):
            speak_tts(client, question)  # Ask the question with TTS

        audio_input = st.audio_input("🎙 Your Answer")  # Capture user's answer

        if audio_input and st.button("💬 Submit Answer", use_container_width=True):
            answer_text = transcribe_audio(client, audio_input)  # Transcribe audio
            st.session_state.transcripts.append({
                "question": question,
                "answer": answer_text
            })
            save_transcript_to_file(question, answer_text)  # Save to transcript file
            st.session_state.current_q += 1
            st.rerun()

    # Interview completed
    else:
        st.success("✅ Interview complete!")

        if st.button("📊 Generate Results", use_container_width=True):
            with st.spinner("Evaluating candidate answers..."):
                chain = evaluate_answer(TRANSCRIPT_FILE, api_key=st.session_state.openai_api_key)

                with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
                    transcript_text = f.read().strip()

                result = chain.run({"transcript": transcript_text})

            st.success("Evaluation Completed ✅")
            st.markdown(result)

            clear_transcript_file()
        if st.button("🔄 END Interview", use_container_width=True):
            st.session_state.current_q = 0
            st.session_state.transcripts = []
            st.rerun()


# Main function to handle navigation between pages
def main():
    st.sidebar.title("Navigation")  # Sidebar navigation
    page = st.sidebar.radio("Go to", ["Generate summary", "Generate Questions", "AI Interview"])
    if page == "Generate summary":
        generate_summary()
    elif page == "Generate Questions":
        generate_questions()
    else:
        ai_interview()

    st.markdown("---")  # Horizontal line
    st.markdown(
        "<div style='text-align: center; color: gray;'>Made with ❤️ for better hiring decisions</div>",
        unsafe_allow_html=True
    )

# Entry point for the Streamlit app
if __name__ == "__main__":
    main()
