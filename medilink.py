import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="MediLink", page_icon="🩺", layout="wide")

st.title("🩺 MediLink: AI Health Assistant")
st.markdown("Upload your medical reports (PDF, JPG, PNG, TXT) for instant analysis.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Your Documents")
    # 1. UPDATE: Accept multiple file types
    uploaded_file = st.file_uploader("Upload Report", type=['pdf', 'jpg', 'jpeg', 'png', 'txt'])
    
    # Secure Key Handling
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("✅ AI Connected")
    else:
        api_key = st.text_input("Enter Google Gemini API Key", type="password")

# --- MAIN LOGIC ---
if uploaded_file is not None and api_key:
    
    # Variable to hold the data we send to AI
    evidence_for_ai = None
    file_type = uploaded_file.type

    # --- PROCESSING LOGIC ---
    try:
        # CASE 1: PDF Files
        if "pdf" in file_type:
            uploaded_file.seek(0) # Fix for EOF Error
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or "" # Handle empty pages safely
            evidence_for_ai = text
            st.info("📄 PDF Loaded successfully.")

        # CASE 2: Text Files
        elif "text" in file_type:
            uploaded_file.seek(0)
            evidence_for_ai = uploaded_file.read().decode("utf-8")
            st.info("📝 Text file loaded successfully.")

        # CASE 3: Images (JPG/PNG)
        elif "image" in file_type:
            uploaded_file.seek(0)
            # Convert to a format Gemini understands (PIL Image)
            evidence_for_ai = Image.open(uploaded_file)
            st.image(evidence_for_ai, caption="Uploaded Image", use_container_width=True)
            st.info("📷 Image loaded. The AI will 'read' this for you.")

        # --- AI CHATBOT ---
        st.divider()
        st.subheader("🤖 Chat with your Report")
        user_question = st.text_input("Ask a question (e.g., 'What is the diagnosis?')")
        
        if user_question and evidence_for_ai:
            client = genai.Client(api_key=api_key)
            
            # Smart Prompting
            sys_prompt = """
            You are a helpful medical assistant. 
            Analyze the provided document (text or image) and answer the user's question.
            Simplify complex medical terms. If the image is handwritten, try your best to read it.
            """
            
            with st.spinner("Analyzing document..."):
                # We send BOTH the prompt and the evidence (Image or Text)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=[evidence_for_ai, sys_prompt, user_question]
                )
                
                st.write(response.text)
                
                # Download Button
                st.download_button(
                    label="📥 Download Summary",
                    data=response.text,
                    file_name="medilink_analysis.txt",
                )
                
    except Exception as e:
        st.error(f"An error occurred: {e}")

elif not api_key:
    st.info("👈 Please enter your API Key to start.")