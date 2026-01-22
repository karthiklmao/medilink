import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time
import io

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MediLink AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. THE "PROXIMA" UI INJECTION (CSS) ---
st.markdown("""
    <style>
    /* IMPORT MODERN FONT */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
    }

    /* NEON GRADIENT BUTTONS */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #8A2BE2 0%, #FF0080 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 0, 128, 0.4);
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(255, 0, 128, 0.6);
        color: white;
    }

    /* GLASSMORPHISM CARDS */
    .stExpander, .stTextInput, .stFileUploader {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: #0a0a14;
        border-right: 1px solid #2a2a35;
    }

    /* CUSTOM TITLES WITH GRADIENT TEXT */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.05);
        border-radius: 20px;
        color: white;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #8A2BE2 0%, #FF0080 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state:
    st.session_state.vault = []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=60)
    st.title("MediLink Portal")
    st.caption("v4.0 | Neon Edition")
    st.markdown("---")
    
    uploaded_file = st.file_uploader("📂 Upload Medical Record", type=['pdf', 'jpg', 'png', 'txt'])
    
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("🟢 System Online")
    else:
        api_key = st.text_input("Access Key", type="password")

    # Vault Stats (Styled)
    st.markdown("---")
    st.markdown(f"**🗄️ Vault Status:** `{len(st.session_state.vault)}` Files")

# --- HELPER FUNCTIONS ---
def get_gemini_response(client, content, prompt):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[content, prompt]
            )
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (attempt + 1) * 5
                st.warning(f"⚠️ High traffic. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Server busy. Please try again.")

def save_to_vault(filename, file_type, content, summary="Not Analyzed"):
    for f in st.session_state.vault:
        if f['name'] == filename: return
    st.session_state.vault.append({
        "name": filename, "type": file_type, "content": content, 
        "summary": summary, "timestamp": time.strftime("%H:%M")
    })

# --- MAIN LAYOUT ---
tab1, tab2 = st.tabs(["⚡ Analysis Console", "🗃️ Secure Vault"])

# ================= TAB 1: CONSOLE =================
with tab1:
    if uploaded_file and api_key:
        col1, col2 = st.columns([1, 1.5], gap="large")

        # --- PROCESS FILE ---
        file_type = uploaded_file.type
        evidence_for_ai = None
        
        if "pdf" in file_type:
            uploaded_file.seek(0)
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages: text += page.extract_text() or ""
            evidence_for_ai = text
            save_to_vault(uploaded_file.name, "PDF", text)

        elif "image" in file_type:
            uploaded_file.seek(0)
            evidence_for_ai = Image.open(uploaded_file)
            save_to_vault(uploaded_file.name, "Image", evidence_for_ai)
            
        elif "text" in file_type:
            uploaded_file.seek(0)
            evidence_for_ai = uploaded_file.read().decode("utf-8")
            save_to_vault(uploaded_file.name, "Text", evidence_for_ai)

        # --- LEFT: PREVIEW ---
        with col1:
            st.subheader("SCAN PREVIEW")
            container = st.container(border=True)
            with container:
                if "image" in file_type:
                    st.image(evidence_for_ai, use_container_width=True)
                else:
                    st.code(str(evidence_for_ai)[:500] + "...", language="text")

        # --- RIGHT: INTELLIGENCE ---
        with col2:
            st.subheader("AI DIAGNOSTICS")
            
            # The "Proxima" style button
            if st.button("RUN ANALYSIS 🚀", type="primary"):
                client = genai.Client(api_key=api_key)
                
                with st.spinner("Decoding medical data..."):
                    try:
                        prompt = """
                        Analyze this medical document.
                        TASK 1: SUMMARY (Plain English, bullet points).
                        TASK 2: JSON DATA of vitals at the very end. Format: [{"Test": "Name", "Value": 10, "Unit": "mg"}]
                        """
                        response = get_gemini_response(client, evidence_for_ai, prompt)
                        
                        # Parsing
                        full_text = response.text
                        try:
                            json_start = full_text.rfind("[")
                            json_end = full_text.rfind("]") + 1
                            summary = full_text[:json_start].strip()
                            data_str = full_text[json_start:json_end]
                            data_json = json.loads(data_str)
                        except:
                            summary = full_text
                            data_json = []

                        # Update Vault
                        for f in st.session_state.vault:
                            if f['name'] == uploaded_file.name: f['summary'] = summary
                        
                        # Display Results
                        st.markdown("### 🧬 Clinical Findings")
                        st.markdown(summary)
                        
                        if data_json:
                            st.markdown("### 📊 Biometrics")
                            df = pd.DataFrame(data_json)
                            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                            st.bar_chart(df.set_index("Test")['Value'], color="#8A2BE2") # Purple Chart
                            
                    except Exception as e:
                        st.error(f"Error: {e}")

    elif not uploaded_file:
        # LANDING PAGE - HERO SECTION
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_main, _ = st.columns([2, 1])
        with col_main:
            st.title("Revolutionizing Health Data.")
            st.markdown("""
            <h3 style='color: #a0a0a0; font-weight: 300;'>
            Your personal medical intelligence hub. Secure. Fast. Powered by Gemini 2.0.
            </h3>
            """, unsafe_allow_html=True)
            st.info("👈 Upload a file to begin the sequence.")

# ================= TAB 2: VAULT =================
with tab2:
    st.subheader("ENCRYPTED ARCHIVE")
    if not st.session_state.vault:
        st.caption("No records found in current session.")
    else:
        for f in st.session_state.vault:
            with st.expander(f"📄 {f['name']} | {f['timestamp']}"):
                st.markdown(f"**Type:** {f['type']}")
                st.info(f"Summary: {f['summary'][:200]}...")