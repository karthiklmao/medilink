import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time
from fpdf import FPDF
import io

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="MediLink",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. COASTAL THEME CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #272838; /* Dark Blue-Black Text */
    }
    
    .stApp {
        background-color: #ECF8FD; /* Light Blue Background */
    }

    /* --- NAVIGATION CONTAINER (Transparent/Invisible) --- */
    div[data-testid="stVerticalBlock"] > div:has(div.nav-button) {
        background-color: transparent; /* Make the box invisible */
        padding: 0rem;
        border: none;
        box-shadow: none;
        margin-bottom: 2rem;
    }

    /* CARDS & INPUTS */
    div.stExpander, div[data-testid="stFileUploader"], div.stDataFrame, div[data-testid="stChatInput"] {
        background: #AFCBD5; /* Soft Blue-Grey */
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #9FB7C1;
        box-shadow: 0px 4px 20px rgba(39, 40, 56, 0.03);
    }
    
    /* --- TRANSPARENT NAVIGATION BUTTONS --- */
    div.stButton > button {
        background-color: transparent !important; /* INVISIBLE BOX */
        color: #272838 !important; /* TEXT COLOR = THEME DARK */
        border: none;
        height: 2.5rem;
        font-weight: 700; /* Bold text to make it stand out */
        font-size: 18px !important;
        transition: all 0.3s ease;
        width: 100%;
        text-align: center;
    }
    
    /* Hover Effect: Subtle Grey Background */
    div.stButton > button:hover {
        background-color: rgba(39, 40, 56, 0.1) !important; 
        color: #272838 !important;
        border-radius: 8px;
    }
    
    /* Fix for paragraph text inside buttons */
    div.stButton > button p { color: #272838 !important; }

    /* --- PRIMARY ACTION BUTTON (Muted Mauve - Kept Solid) --- */
    button[kind="primary"] {
        background-color: #815355 !important;
        color: white !important; /* Keep white text for main button */
        height: 3rem !important;
        font-weight: 700 !important;
        border-radius: 8px;
    }
    button[kind="primary"] p { color: white !important; } /* Force white text */
    
    button[kind="primary"]:hover {
        background-color: #6B4446 !important;
        box-shadow: 0 4px 14px rgba(129, 83, 85, 0.4) !important;
    }
    
    /* LOGO TEXT - ENLARGED TO 45px */
    .logo-text {
        font-weight: 800;
        font-size: 45px; /* REQUESTED SIZE */
        color: #272838;
        letter-spacing: -1px;
        line-height: 1.0;
        padding-top: 5px;
    }
    
    /* STATUS BADGE */
    .status-badge {
        background-color: #D0E3ED;
        color: #272838;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #815355;
        text-align: center;
    }
    
    h1, h2, h3, h4, h5, h6, p, li { color: #272838; }
    .stTextInput input { border: 1px solid #815355; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state: st.session_state.vault = []
if "page" not in st.session_state: st.session_state.page = "Home"
if "current_report" not in st.session_state: st.session_state.current_report = ""
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 4. TOP NAVIGATION BAR ---
with st.container():
    col_logo, col_nav_space, col_nav_buttons, col_end_space, col_status = st.columns([3, 0.5, 5, 0.5, 2])
    
    with col_logo:
        st.markdown('<p class="logo-text">MEDILINK</p>', unsafe_allow_html=True)
        
    with col_nav_buttons:
        # Align buttons to the bottom of the container to match logo baseline
        st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
        nav_1, nav_2, nav_3 = st.columns(3)
        with nav_1:
            if st.button("Home", use_container_width=True): st.session_state.page = "Home"
        with nav_2:
            if st.button("Trends", use_container_width=True): st.session_state.page = "Trends"
        with nav_3:
            if st.button("Files", use_container_width=True): st.session_state.page = "Files"
                
    with col_status:
        st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="status-badge">● Secure Connection</div>', unsafe_allow_html=True)

st.markdown("---")

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

def create_pdf(summary, action_plan):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(40, 10, 'MediLink AI Health Report')
    pdf.ln(20)
    
    pdf.set_font("Arial", '', 12)
    content = f"Clinical Summary:\n\n{summary}\n\nAction Plan:\n\n{action_plan}"
    content = content.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, content)
    return pdf.output(dest='S').encode('latin-1')

def save_to_vault(name, type, content, summary="Pending", data=None, date=None):
    for f in st.session_state.vault:
        if f['name'] == name: return
    st.session_state.vault.append({
        "name": name, 
        "type": type, 
        "content": content, 
        "summary": summary, 
        "data": data if data else [],
        "date": date if date else time.strftime("%Y-%m-%d"),
        "timestamp": time.strftime("%H:%M")
    })

# --- PAGE LOGIC ---

# ================= PAGE 1: HOME =================
if st.session_state.page == "Home":
    st.markdown("### Home")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

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
                    st.info(f"{len(reader.pages)} Pages Processed")
                elif "image" in file_type:
                    uploaded_file.seek(0)
                    evidence = Image.open(uploaded_file)
                    st.image(evidence, use_container_width=True)
                elif "text" in file_type:
                    uploaded_file.seek(0)
                    evidence = uploaded_file.read().decode("utf-8")
                    st.text_area("Content", evidence[:200], height=150)

                save_to_vault(uploaded_file.name, "File", evidence)

        with col2:
            st.markdown("##### Intelligence Console")
            if uploaded_file:
                if st.button("Run Diagnostics", type="primary"):
                    client = genai.Client(api_key=api_key)
                    with st.spinner("Analyzing..."):
                        try:
                            prompt = """
                            Act as a senior medical analyst. 
                            TASK 1: SUMMARY. Write a clear summary.
                            TASK 2: VITALS. JSON list at end: [{"Test":"Name", "Value":0, "Unit":"x"}].
                            TASK 3: ACTION PLAN. List 3 specific lifestyle changes based on this data.
                            TASK 4: DATE. Extract the report date as YYYY-MM-DD. If none, say "TODAY".
                            """
                            response = get_gemini_response(client, evidence, prompt)
                            full_text = response.text
                            
                            try:
                                j_start, j_end = full_text.rfind("["), full_text.rfind("]") + 1
                                data_part = full_text[j_start:j_end]
                                data_json = json.loads(data_part)
                                summary_text = full_text[:j_start].strip()
                            except:
                                summary_text = full_text
                                data_json = []

                            st.session_state.current_report = summary_text
                            st.session_state.current_data = data_json
                            
                            for f in st.session_state.vault:
                                if f['name'] == uploaded_file.name:
                                    f['summary'] = summary_text
                                    f['data'] = data_json
                            
                        except Exception as e:
                            st.error(f"Error: {e}")

                if st.session_state.current_report:
                    tab_sum, tab_chat, tab_export = st.tabs(["📊 Report", "💬 Doc Talk", "📥 Export"])
                    
                    with tab_sum:
                        st.markdown(st.session_state.current_report)
                        if "current_data" in st.session_state and st.session_state.current_data:
                            df = pd.DataFrame(st.session_state.current_data)
                            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                            st.bar_chart(df.set_index("Test")['Value'], color="#815355")

                    with tab_chat:
                        st.markdown("##### Ask Dr. AI")
                        user_query = st.text_input("Ask a question about this report:", placeholder="e.g., Is my iron low?")
                        if user_query:
                            client = genai.Client(api_key=api_key)
                            chat_prompt = f"Context: {st.session_state.current_report}. Question: {user_query}. Keep it short and medical."
                            with st.spinner("Thinking..."):
                                answer = get_gemini_response(client, "Context Provided", chat_prompt)
                                st.info(f"**AI:** {answer.text}")

                    with tab_export:
                        st.markdown("##### Official Download")
                        if st.button("Generate PDF Report"):
                            pdf_bytes = create_pdf(st.session_state.current_report, "See Summary for details.")
                            st.download_button(
                                label="Download PDF",
                                data=pdf_bytes,
                                file_name="medilink_report.pdf",
                                mime="application/pdf"
                            )
            else:
                st.info("Awaiting file upload...")

# ================= PAGE 2: TRENDS =================
elif st.session_state.page == "Trends":
    st.markdown("### Health Trends")
    st.markdown("Longitudinal analysis of your uploaded records.")
    
    if not st.session_state.vault:
        st.info("Upload multiple reports in 'Home' to see trends here.")
    else:
        all_vitals = []
        for f in st.session_state.vault:
            if f.get('data'):
                for item in f['data']:
                    all_vitals.append({
                        "Date": f['timestamp'],
                        "Test": item['Test'],
                        "Value": item['Value']
                    })
        
        if all_vitals:
            df_trends = pd.DataFrame(all_vitals)
            df_trends['Value'] = pd.to_numeric(df_trends['Value'], errors='coerce')
            
            tests = df_trends['Test'].unique()
            selected_test = st.selectbox("Select Vital Sign to Track", tests)
            
            chart_data = df_trends[df_trends['Test'] == selected_test]
            st.line_chart(chart_data.set_index("Date")['Value'], color="#815355")
            
            st.markdown(f"""
            <div style="background-color: #AFCBD5; padding: 20px; border-radius: 10px; border-left: 5px solid #815355;">
                <b>Insight:</b> Tracking <b>{selected_test}</b> across {len(chart_data)} data points.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No numerical data found in your uploaded reports yet.")

# ================= PAGE 3: FILES =================
elif st.session_state.page == "Files":
    st.markdown("### Secure Archive")
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