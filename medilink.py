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
    initial_sidebar_state="expanded"
)

# --- 2. BOUTIQUE EARTH THEME CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #27231E; /* Eerie Black */
    }
    
    .stApp {
        background-color: #FFF5F5; /* Snow */
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #EAEAEA;
    }
    
    div.stExpander, div[data-testid="stFileUploader"], div.stDataFrame {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #F0F0F0;
        box-shadow: 0px 4px 20px rgba(39, 35, 30, 0.03);
    }
    
    /* --- FIXED BUTTON STYLING --- */
    /* Target all buttons to have white text */
    div.stButton > button {
        background-color: #3A5253 !important; /* Dark Slate Gray */
        color: #FFFFFF !important; /* PURE WHITE TEXT */
        border-radius: 8px;
        border: none;
        height: 3rem;
        font-weight: 500;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    /* Ensure text stays white on hover */
    div.stButton > button:hover {
        background-color: #27231E !important; 
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(58, 82, 83, 0.2);
    }
    
    /* Ensure text stays white when clicked/focused */
    div.stButton > button:focus:not(:active) {
        color: #FFFFFF !important;
        background-color: #3A5253 !important;
    }
    
    /* Target the paragraph tag inside the button specifically (Streamlit quirk) */
    div.stButton > button p {
        color: #FFFFFF !important; 
    }

    /* ACTION BUTTON (Burnt Sienna - Different Color) */
    button[kind="primary"] {
        background-color: #E07A5F !important;
        color: white !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(224, 122, 95, 0.3) !important;
    }
    button[kind="primary"]:hover {
        background-color: #C85D40 !important;
    }

    .premium-card {
        background: linear-gradient(135deg, #3A5253 0%, #27231E 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        margin-top: 20px;
        text-align: left;
        position: relative;
        overflow: hidden;
    }
    .premium-card h3 {
        color: #FFFFFF !important;
        font-size: 18px;
        margin: 0 0 5px 0;
        font-weight: 600;
    }
    .premium-card p {
        color: #81B29A;
        font-size: 13px;
        margin: 0 0 15px 0;
    }
    
    h1, h2, h3 { color: #27231E; }
    p, li { color: #3A5253; }
    
    .stTextInput input {
        border: 1px solid #81B29A;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state: st.session_state.vault = []
if "page" not in st.session_state: st.session_state.page = "Home"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### MEDILINK")
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    # Navigation Buttons (White Text Fixed)
    if st.button("Home"):
        st.session_state.page = "Home"
        
    if st.button("Files"):
        st.session_state.page = "Files"
        
    st.markdown("<div style='height: 50px'></div>", unsafe_allow_html=True)
    
    # Sidebar Card
    st.markdown("""
    <div class="premium-card">
        <h3>Pro Account</h3>
        <p>Secure Connection</p>
        <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px;">
            <div style="width: 70%; height: 100%; background: #81B29A; border-radius: 2px;"></div>
        </div>
        <div style="font-size: 10px; color: rgba(255,255,255,0.6); margin-top: 8px;">
            System Operational
        </div>
    </div>
    """, unsafe_allow_html=True)

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

# HEADER (No Search Bar)
st.markdown(f"## {st.session_state.page}")
st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

# PAGE 1: HOME
if st.session_state.page == "Home":
    
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        api_key = st.text_input("License Key", type="password")

    if api_key:
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            st.markdown("##### Upload")
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
                if uploaded_file and st.button("Run Diagnostics", type="primary"):
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
                elif not uploaded_file:
                    st.info("Awaiting file upload...")

# PAGE 2: FILES (Vault)
elif st.session_state.page == "Files":
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