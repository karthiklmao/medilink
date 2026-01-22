import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MediLink 365",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. MICROSOFT STYLE CSS ---
st.markdown("""
    <style>
    /* IMPORT MODERN FONT (Segoe UI equivalent) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    /* REMOVE DEFAULT STREAMLIT PADDING */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* TOP NAVIGATION BAR */
    .nav-container {
        background-color: #f0f2f5;
        padding: 10px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid #0078d4; /* Microsoft Blue */
    }

    /* BUTTONS (Microsoft Blue Style) */
    div.stButton > button:first-child {
        background-color: #0078d4;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #106ebe;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* CARDS */
    .stExpander, .stTextInput, div[data-testid="stFileUploader"] {
        background-color: #ffffff;
        border: 1px solid #e1dfdd;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* HEADERS */
    h1, h2, h3 {
        color: #201f1e;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state:
    st.session_state.vault = []
if "page" not in st.session_state:
    st.session_state.page = "Home"

# --- 4. TOP NAVIGATION BAR (The "Microsoft" Ribbon) ---
# We use columns to create a horizontal header
col_logo, col_nav1, col_nav2, col_auth = st.columns([1, 1, 1, 2])

with col_logo:
    st.markdown("### 🩺 MediLink 365")

with col_nav1:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"

with col_nav2:
    if st.button("🗄️ Vault", use_container_width=True):
        st.session_state.page = "Vault"

with col_auth:
    # KEY HANDLING IN HEADER
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("🔒 Enterprise Access Active")
    else:
        api_key = st.text_input("Enter API Key", type="password", label_visibility="collapsed", placeholder="Enter API Key")

st.markdown("---") # Divider line below header

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
                st.warning(f"⚠️ Server Busy. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Service unavailable. Try again later.")

def save_to_vault(filename, file_type, content, summary="Not Analyzed"):
    for f in st.session_state.vault:
        if f['name'] == filename: return
    st.session_state.vault.append({
        "name": filename, "type": file_type, "content": content, 
        "summary": summary, "timestamp": time.strftime("%H:%M")
    })

# --- PAGE ROUTING LOGIC ---

# ==========================================
# PAGE 1: HOME (Dashboard)
# ==========================================
if st.session_state.page == "Home":
    st.subheader("Dashboard")
    
    # 1. FILE UPLOAD SECTION (Top Card)
    with st.container():
        uploaded_file = st.file_uploader("Upload Document to Cloud", type=['pdf', 'jpg', 'png', 'txt'])

    if uploaded_file and api_key:
        col1, col2 = st.columns([1, 1.5], gap="large")

        # --- PREPARE DATA ---
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

        # --- LEFT: PREVIEWER ---
        with col1:
            st.markdown("**Document Preview**")
            if "image" in file_type:
                st.image(evidence_for_ai, use_container_width=True)
            else:
                st.text_area("Content", str(evidence_for_ai)[:800], height=300)

        # --- RIGHT: AI ANALYSIS ---
        with col2:
            st.markdown("**AI Insights**")
            
            if st.button("Generate Report", type="primary"):
                client = genai.Client(api_key=api_key)
                
                with st.spinner("Analyzing data..."):
                    try:
                        prompt = """
                        Analyze this document.
                        TASK 1: SUMMARY (Plain English).
                        TASK 2: JSON DATA of vitals at end. Format: [{"Test": "Name", "Value": 10, "Unit": "mg"}]
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
                        
                        st.success("Analysis Complete")
                        st.markdown(summary)
                        
                        if data_json:
                            st.divider()
                            st.markdown("**Vitals Trend**")
                            df = pd.DataFrame(data_json)
                            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                            st.bar_chart(df.set_index("Test")['Value'])
                            
                    except Exception as e:
                        st.error(f"Error: {e}")

    elif not uploaded_file:
        # Empty State
        st.info("👋 Welcome. Please upload a medical record to begin analysis.")

# ==========================================
# PAGE 2: VAULT (Storage)
# ==========================================
elif st.session_state.page == "Vault":
    st.subheader("🗄️ Secure Document Vault")
    
    if not st.session_state.vault:
        st.warning("Vault is empty. Go to Home to upload files.")
    else:
        # Display as a table/list
        for f in st.session_state.vault:
            with st.expander(f"{f['type']} - {f['name']} ({f['timestamp']})"):
                st.markdown(f"**AI Summary:**")
                st.write(f['summary'])