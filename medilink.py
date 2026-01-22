import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="MediLink Horizon",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. HORIZON DASHBOARD CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #2B3674;
    }
    
    /* HIDE DEFAULT STREAMLIT ELEMENTS */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* BACKGROUND */
    .stApp {
        background-color: #F4F7FE;
    }

    /* SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        box-shadow: 2px 0 5px rgba(0,0,0,0.02);
    }
    
    /* CARDS (White floating boxes) */
    div.stExpander, div[data-testid="stFileUploader"], div.stDataFrame {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        border: none;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.03);
    }
    
    /* BUTTONS (Horizon Purple) */
    div.stButton > button:first-child {
        background-color: #4318FF;
        color: white;
        border-radius: 12px;
        padding: 0.5rem 2rem;
        border: none;
        font-weight: 700;
        box-shadow: 0 4px 10px rgba(67, 24, 255, 0.2);
    }
    div.stButton > button:first-child:hover {
        background-color: #3311db;
    }

    /* CUSTOM GRADIENT CARD IN SIDEBAR */
    .gradient-card {
        background: linear-gradient(135deg, #868CFF 0%, #4318FF 100%);
        border-radius: 20px;
        padding: 20px;
        color: white;
        margin-top: 20px;
        text-align: center;
    }
    .gradient-card h3 {
        color: white !important;
        font-size: 16px;
        margin: 0;
    }
    .gradient-card p {
        color: rgba(255,255,255,0.8);
        font-size: 12px;
        margin: 5px 0 15px 0;
    }

    /* HEADER TEXT */
    h1, h2, h3 {
        color: #1B2559;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state: st.session_state.vault = []
if "page" not in st.session_state: st.session_state.page = "Dashboard"

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("### <span style='color:#4318FF'>HORIZON</span> MEDILINK", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Navigation Buttons (Styled as Menu)
    if st.button("🏠  Dashboard", use_container_width=True):
        st.session_state.page = "Dashboard"
        
    if st.button("📂  My Vault", use_container_width=True):
        st.session_state.page = "Vault"
        
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    # THE PURPLE GRADIENT CARD (Like the reference image)
    st.markdown("""
    <div class="gradient-card">
        <div style="background:rgba(255,255,255,0.2); width:40px; height:40px; border-radius:50%; margin:0 auto 10px auto; display:flex; align-items:center; justify-content:center;">
            🧬
        </div>
        <h3>MediLink Pro</h3>
        <p>Your secure medical cloud is active.</p>
        <div style="background:rgba(255,255,255,0.3); border-radius:10px; padding:5px; font-size:12px;">
            Secure Connection
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

# 1. HEADER (Top Right Search Bar Mockup)
col_title, col_search = st.columns([3, 1])
with col_title:
    st.markdown(f"# {st.session_state.page}")
    st.caption("Overview of your medical data intelligence.")

with col_search:
    # A visual search bar (mockup for style)
    st.text_input("Search", placeholder="🔍 Search...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# 2. DASHBOARD CONTENT
if st.session_state.page == "Dashboard":
    
    # API KEY CHECK
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        api_key = st.text_input("Enter License Key", type="password")

    if api_key:
        # Layout: Upload (Left) vs Analysis (Right)
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            st.markdown("##### Upload Record")
            uploaded_file = st.file_uploader("Drop PDF/Image", type=['pdf', 'jpg', 'png', 'txt'], label_visibility="collapsed")
            
            if uploaded_file:
                st.markdown("##### Preview")
                file_type = uploaded_file.type
                evidence = None
                
                # Processing
                if "pdf" in file_type:
                    uploaded_file.seek(0)
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text = "".join([p.extract_text() for p in reader.pages])
                    evidence = text
                    save_to_vault(uploaded_file.name, "PDF", text)
                    st.info(f"PDF: {len(reader.pages)} Pages")

                elif "image" in file_type:
                    uploaded_file.seek(0)
                    evidence = Image.open(uploaded_file)
                    save_to_vault(uploaded_file.name, "Image", evidence)
                    st.image(evidence, use_container_width=True)
                    
                elif "text" in file_type:
                    uploaded_file.seek(0)
                    evidence = uploaded_file.read().decode("utf-8")
                    save_to_vault(uploaded_file.name, "Text", evidence)
                    st.text_area("Raw", evidence[:200], height=100)

        with col2:
            st.markdown("##### Intelligence Console")
            # Create a white card for results
            with st.container():
                if uploaded_file and st.button("Run AI Diagnostics"):
                    client = genai.Client(api_key=api_key)
                    with st.spinner("Processing..."):
                        try:
                            prompt = """
                            Medical Analysis.
                            1. Summary (Plain English).
                            2. JSON Vitals [{"Test":"Name", "Value":0}].
                            """
                            response = get_gemini_response(client, evidence, prompt)
                            
                            # Parse
                            txt = response.text
                            try:
                                j_start, j_end = txt.rfind("["), txt.rfind("]") + 1
                                summary, data = txt[:j_start].strip(), json.loads(txt[j_start:j_end])
                            except:
                                summary, data = txt, []

                            # Update Vault
                            for f in st.session_state.vault:
                                if f['name'] == uploaded_file.name: f['summary'] = summary
                            
                            st.success("Analysis Complete")
                            st.markdown(summary)
                            
                            if data:
                                st.markdown("##### Vitals Trend")
                                df = pd.DataFrame(data)
                                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                                st.bar_chart(df.set_index("Test")['Value'], color="#4318FF") # Purple Chart
                                
                        except Exception as e:
                            st.error(f"Error: {e}")
                elif not uploaded_file:
                    st.info("Waiting for upload...")

# 3. VAULT CONTENT
elif st.session_state.page == "Vault":
    if not st.session_state.vault:
        st.info("No records found.")
    else:
        for f in st.session_state.vault:
            # Display as nice white cards
            with st.expander(f"📄 {f['name']} ({f['timestamp']})"):
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    st.caption("TYPE")
                    st.markdown(f"**{f['type']}**")
                with col_b:
                    st.caption("SUMMARY")
                    st.write(f['summary'])