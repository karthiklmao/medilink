import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="MediLink",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed" # Hides the empty sidebar
)

# --- 2. BOUTIQUE EARTH THEME CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #27231E;
    }
    
    .stApp {
        background-color: #FFF5F5; /* Snow Background */
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* --- TOP NAVIGATION BAR CONTAINER --- */
    div[data-testid="stVerticalBlock"] > div:has(div.nav-button) {
        background-color: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        margin-bottom: 2rem;
    }

    /* CARDS */
    div.stExpander, div[data-testid="stFileUploader"], div.stDataFrame {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #F0F0F0;
        box-shadow: 0px 4px 20px rgba(39, 35, 30, 0.03);
    }
    
    /* --- NAVIGATION BUTTONS (Dark Slate Gray) --- */
    div.stButton > button {
        background-color: #3A5253 !important; 
        color: #FFFFFF !important; /* Force White Text */
        border-radius: 8px;
        border: none;
        height: 2.5rem; /* Slightly shorter for top bar */
        font-weight: 500;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    div.stButton > button:hover {
        background-color: #27231E !important; 
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(58, 82, 83, 0.2);
    }
    
    div.stButton > button:focus:not(:active) {
        color: #FFFFFF !important;
        background-color: #3A5253 !important;
    }
    
    div.stButton > button p {
        color: #FFFFFF !important; 
    }

    /* PRIMARY ACTION BUTTON (Burnt Sienna) */
    button[kind="primary"] {
        background-color: #E07A5F !important;
        height: 3rem !important; /* Taller for main action */
    }
    button[kind="primary"]:hover {
        background-color: #C85D40 !important;
    }
    
    /* LOGO TEXT */
    .logo-text {
        font-weight: 700;
        font-size: 24px;
        color: #27231E;
        letter-spacing: -0.5px;
        padding-top: 5px;
    }
    
    /* STATUS INDICATOR */
    .status-badge {
        background-color: #E6F4F1;
        color: #3A5253;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #81B29A;
        text-align: center;
    }
    
    h1, h2, h3 { color: #27231E; }
    .stTextInput input {
        border: 1px solid #81B29A;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state: st.session_state.vault = []
if "page" not in st.session_state: st.session_state.page = "Home"

# --- 4. TOP NAVIGATION BAR ---
# We create a container to hold the top bar elements
with st.container():
    # Layout: Logo (Left) | Nav Buttons (Middle) | Status (Right)
    col_logo, col_nav_space, col_nav_buttons, col_end_space, col_status = st.columns([2, 1, 4, 1, 2])
    
    with col_logo:
        st.markdown('<p class="logo-text">MEDILINK</p>', unsafe_allow_html=True)
        
    with col_nav_buttons:
        # Nested columns to center the buttons next to each other
        nav_1, nav_2 = st.columns(2)
        with nav_1:
            if st.button("Home", use_container_width=True):
                st.session_state.page = "Home"
        with nav_2:
            if st.button("Files", use_container_width=True):
                st.session_state.page = "Files"
                
    with col_status:
        # A small badge showing the system is secure
        st.markdown('<div class="status-badge">● Secure Connection</div>', unsafe_allow_html=True)

st.markdown("---") # Divider line

# --- HELPER FUNCTIONS ---
def get_gemini_response(client, content, prompt):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model="gemini-2.0-flash", contents=[content, prompt])
        except Exception as e:
            if "429" in str(e):
                time.sleep((attempt + 1) * 5)
            else:
                raise e
    raise Exception("Service busy.")

def save_to_vault(name, type, content, summary="Pending"):
    for f in st.session_state.vault:
        if f['name'] == name: return
    st.session_state.vault.append({"name": name, "type": type, "content": content, "summary": summary, "timestamp": time.strftime("%H:%M")})

# --- PAGE LOGIC ---

# PAGE 1: HOME
if st.session_state.page == "Home":
    
    # Header area
    st.markdown("### Dashboard")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    # API Key Input (if needed)
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        api_key = st.text_input("License Key", type="password")

    if api_key:
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            st.markdown("##### Upload Record")
            uploaded_file = st.file_uploader("Upload", type=['pdf', 'jpg', 'png', 'txt'], label_visibility="collapsed")
            
            if uploaded_file:
                st.markdown("##### Preview")
                file_type = uploaded_file.type
                evidence = None
                
                if "pdf" in file_type:
                    uploaded_file.seek(0)
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text = "".join([p.extract_text() for p in reader.pages])
                    evidence = text
                    save_to_vault(uploaded_file.name, "PDF", text)
                    st.info(f"{len(reader.pages)} Pages Processed")

                elif "image" in file_type:
                    uploaded_file.seek(0)
                    evidence = Image.open(uploaded_file)
                    save_to_vault(uploaded_file.name, "Image", evidence)
                    st.image(evidence, use_container_width=True)
                    
                elif "text" in file_type:
                    uploaded_file.seek(0)
                    evidence = uploaded_file.read().decode("utf-8")
                    save_to_vault(uploaded_file.name, "Text", evidence)
                    st.text_area("Content", evidence[:200], height=150)

        with col2:
            st.markdown("##### Intelligence Console")
            with st.container():
                if uploaded_file:
                    if st.button("Run Diagnostics", type="primary"):
                        client = genai.Client(api_key=api_key)
                        with st.spinner("Processing..."):
                            try:
                                prompt = """
                                Medical Analysis.
                                1. Summary (Plain English).
                                2. JSON Vitals [{"Test":"Name", "Value":0}].
                                """
                                response = get_gemini_response(client, evidence, prompt)
                                
                                txt = response.text
                                try:
                                    j_start, j_end = txt.rfind("["), txt.rfind("]") + 1
                                    summary, data = txt[:j_start].strip(), json.loads(txt[j_start:j_end])
                                except:
                                    summary, data = txt, []

                                for f in st.session_state.vault:
                                    if f['name'] == uploaded_file.name: f['summary'] = summary
                                
                                st.success("Complete")
                                st.markdown(summary)
                                
                                if data:
                                    st.markdown("##### Trends")
                                    df = pd.DataFrame(data)
                                    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                                    st.bar_chart(df.set_index("Test")['Value'], color="#81B29A")
                                    
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.info("Awaiting file upload...")

# PAGE 2: FILES (Vault)
elif st.session_state.page == "Files":
    st.markdown("### Secure Archive")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

    if not st.session_state.vault:
        st.info("No records found.")
    else:
        for f in st.session_state.vault:
            with st.expander(f"{f['name']}   |   {f['timestamp']}"):
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    st.caption("TYPE")
                    st.write(f['type'])
                with col_b:
                    st.caption("SUMMARY")
                    st.write(f['summary'])