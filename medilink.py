import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MediLink Enterprise",
    page_icon=None, # Removed emoji icon
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CORPORATE SAAS CSS (The "NeuralAgency" Look) ---
st.markdown("""
    <style>
    /* IMPORT INTER FONT (Standard for high-end apps) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
        color: #1E293B;
    }

    /* REMOVE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* CUSTOM NAVIGATION BAR */
    .nav-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 2rem;
        background: white;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 2rem;
    }

    /* HERO TYPOGRAPHY */
    h1 {
        font-weight: 800;
        font-size: 2.5rem;
        color: #0F172A;
        letter-spacing: -0.05rem;
    }
    h3 {
        font-weight: 600;
        color: #334155;
    }
    p {
        color: #64748B;
        font-size: 1rem;
    }

    /* BUTTON STYLING (The Blue "Get Started" Look) */
    div.stButton > button:first-child {
        background-color: #2563EB; /* Corporate Blue */
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    div.stButton > button:first-child:hover {
        background-color: #1D4ED8;
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
    }
    
    /* CARDS (White boxes with shadow) */
    div[data-testid="stExpander"], div[data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 1rem;
    }
    
    /* INPUT FIELDS */
    .stTextInput input {
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. STATE MANAGEMENT ---
if "vault" not in st.session_state:
    st.session_state.vault = []
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# --- 4. TOP NAVIGATION (Text Only) ---
col_brand, col_spacer, col_nav1, col_nav2 = st.columns([2, 6, 1, 1])

with col_brand:
    st.markdown("### MediLink Enterprise")

with col_nav1:
    if st.button("Dashboard", key="nav_home", use_container_width=True):
        st.session_state.page = "Dashboard"

with col_nav2:
    if st.button("Archive", key="nav_vault", use_container_width=True):
        st.session_state.page = "Vault"

st.markdown("---")

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
                st.warning(f"High traffic volume. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Service unavailable. Please try again later.")

def save_to_vault(filename, file_type, content, summary="Pending Analysis"):
    for f in st.session_state.vault:
        if f['name'] == filename: return
    st.session_state.vault.append({
        "name": filename, "type": file_type, "content": content, 
        "summary": summary, "timestamp": time.strftime("%Y-%m-%d %H:%M")
    })

# --- PAGE LOGIC ---

# ==========================================
# PAGE 1: DASHBOARD (The "Home" View)
# ==========================================
if st.session_state.page == "Dashboard":
    
    # HERO SECTION (Like the reference image)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px;">
        <h1 style="margin-bottom: 10px;">Create Trustworthy Medical Insights.</h1>
        <p style="font-size: 1.2rem; max-width: 600px; margin: 0 auto;">
            Robust observability, analytics, and assessment for your medical documents.
            Powered by Gemini 2.0 Flash.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # API KEY CHECK (Subtle)
    if "GEMINI_KEY" not in st.secrets:
        st.warning("System Notice: API License Key required for processing.")
        api_key = st.text_input("Enter License Key", type="password")
    else:
        api_key = st.secrets["GEMINI_KEY"]

    # MAIN WORKSPACE
    if api_key:
        col_upload, col_display = st.columns([1, 2], gap="large")

        with col_upload:
            st.markdown("#### Document Input")
            st.markdown("Supported formats: PDF, PNG, JPG, TXT")
            uploaded_file = st.file_uploader("Drop file here", label_visibility="collapsed", type=['pdf', 'jpg', 'png', 'txt'])

        with col_display:
            if uploaded_file:
                # PROCESS FILE
                file_type = uploaded_file.type
                evidence = None
                
                if "pdf" in file_type:
                    uploaded_file.seek(0)
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text = ""
                    for page in reader.pages: text += page.extract_text() or ""
                    evidence = text
                    save_to_vault(uploaded_file.name, "PDF Document", text)

                elif "image" in file_type:
                    uploaded_file.seek(0)
                    evidence = Image.open(uploaded_file)
                    save_to_vault(uploaded_file.name, "Scanned Image", evidence)
                    
                elif "text" in file_type:
                    uploaded_file.seek(0)
                    evidence = uploaded_file.read().decode("utf-8")
                    save_to_vault(uploaded_file.name, "Raw Text", evidence)

                # ANALYSIS UI
                st.markdown("#### Analysis Console")
                
                # Preview
                with st.expander("View Source Content", expanded=False):
                    if "image" in file_type:
                        st.image(evidence, use_container_width=True)
                    else:
                        st.text(str(evidence)[:1000])

                # Action
                if st.button("Run Diagnostics"):
                    client = genai.Client(api_key=api_key)
                    with st.spinner("Processing request..."):
                        try:
                            prompt = """
                            Act as a professional medical analyst.
                            1. Summary: Provide a clear, technical but accessible summary.
                            2. Vitals: Extract vitals into a JSON list at the end: [{"Test": "Name", "Value": 0, "Unit": "x"}]
                            """
                            response = get_gemini_response(client, evidence, prompt)
                            
                            # Parse
                            full_text = response.text
                            try:
                                json_start = full_text.rfind("[")
                                json_end = full_text.rfind("]") + 1
                                summary = full_text[:json_start].strip()
                                data_str = full_text[json_start:json_end]
                                data = json.loads(data_str)
                            except:
                                summary = full_text
                                data = []

                            # Update Vault
                            for f in st.session_state.vault:
                                if f['name'] == uploaded_file.name: f['summary'] = summary
                            
                            st.success("Diagnostics Complete")
                            st.markdown(summary)
                            
                            if data:
                                st.markdown("#### Biometric Trends")
                                df = pd.DataFrame(data)
                                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                                st.bar_chart(df.set_index("Test")['Value'])
                                
                        except Exception as e:
                            st.error(f"System Error: {e}")

            else:
                # EMPTY STATE (Clean)
                st.info("Awaiting document upload to begin analysis.")

# ==========================================
# PAGE 2: ARCHIVE (The "Vault")
# ==========================================
elif st.session_state.page == "Vault":
    st.markdown("### Secure Archive")
    st.markdown("Session history and processed reports.")
    
    if not st.session_state.vault:
        st.markdown("*No records found in current session.*")
    else:
        for f in st.session_state.vault:
            with st.expander(f"{f['name']} | {f['timestamp']}"):
                st.markdown(f"**Format:** {f['type']}")
                st.markdown("**Executive Summary:**")
                st.write(f['summary'])