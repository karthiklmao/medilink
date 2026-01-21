import streamlit as st
import PyPDF2
from google import genai 

# --- PAGE SETUP ---
st.set_page_config(page_title="MediLink", page_icon="🩺", layout="wide")

st.title("🩺 MediLink: AI Health Assistant")
st.markdown("Upload your medical reports (PDF) to get instant insights.")

# --- SIDEBAR (The "Cloud" Storage) ---
# ... (Keep imports and page setup same as before) ...

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Your Documents")
    uploaded_file = st.file_uploader("Upload a Medical Report", type=["pdf"])
    
    # SMART KEY HANDLING:
    # 1. Check if the key is hidden in the cloud secrets
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("✅ AI Connected (License Active)")
    # 2. If not, ask the user (Fallback mode)
    else:
        api_key = st.text_input("Enter Google Gemini API Key", type="password")
        st.caption("Get your key from: aistudio.google.com")

# ... (Rest of the logic remains exactly the same) ...

# --- MAIN LOGIC ---
if uploaded_file is not None and api_key:
    # 1. Read the PDF locally
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
            
        st.success("✅ Document processed successfully!")
        
        # Show preview
        with st.expander("View Extracted Text"):
            st.write(text[:1000] + "...") 

        # --- AI CHATBOT SECTION ---
        st.divider()
        st.subheader("🤖 Chat with your Report")
        user_question = st.text_input("Ask a question (e.g., 'Is my Iron level normal?')")
        
        if user_question:
            # 2. Configure the New 2025 Client
            client = genai.Client(api_key=api_key)
            
            # 3. Create the Prompt
            prompt = f"""
            You are a helpful medical assistant. 
            Analyze the following medical report text and answer the user's question.
            Simplify complex medical terms into plain English.
            
            Report Text: {text}
            
            User Question: {user_question}
            """
            
            with st.spinner("Analyzing report..."):
                # 4. Generate Content (New Syntax)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                st.write(response.text)
                
    except Exception as e:
        st.error(f"Error reading PDF: {e}")

elif not api_key:
    st.info("👈 Please enter your API Key in the sidebar to start.")