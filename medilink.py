import streamlit as st
import PyPDF2
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import time
from fpdf import FPDF
import io
from gtts import gTTS
import os

# --- 1. PAGE CONFIG ---
icon_path = "medilink_logo.png"
page_icon = Image.open(icon_path) if os.path.exists(icon_path) else None

st.set_page_config(
    page_title="MediLink",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. COASTAL THEME CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: #272838 !important;
    }
    
    .stApp {
        background-color: #ECF8FD;
    }

    div[data-testid="stVerticalBlock"] > div:has(div.nav-button) {
        background-color: transparent;
        padding: 0rem;
        border: none;
        box-shadow: none;
        margin-bottom: 2rem;
    }

    div.stExpander, div[data-testid="stFileUploader"], div.stDataFrame, div[data-testid="stChatInput"] {
        background: #AFCBD5;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #9FB7C1;
        box-shadow: 0px 4px 20px rgba(39, 40, 56, 0.03);
    }
    
    div.stButton > button {
        background-color: transparent !important;
        color: #272838 !important;
        border: 1px solid transparent;
        height: 3rem;
        font-weight: 700;
        font-size: 20px !important;
        transition: all 0.3s ease;
        width: 100%;
        text-align: center;
        padding-top: 5px;
    }
    
    div.stButton > button:hover {
        background-color: rgba(39, 40, 56, 0.05) !important; 
        border: 1px solid #9FB7C1 !important;
        border-radius: 8px;
    }
    
    div.stButton > button p { color: #272838 !important; }

    button[kind="primary"] {
        background-color: #815355 !important;
        color: white !important;
        height: 3rem !important;
        font-weight: 700 !important;
        border-radius: 8px;
    }
    button[kind="primary"] p { color: white !important; }
    
    button[kind="primary"]:hover {
        background-color: #6B4446 !important;
        box-shadow: 0 4px 14px rgba(129, 83, 85, 0.4) !important;
    }
    
    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #272838 !important;
        border: 1px solid #815355 !important;
        height: 2.5rem !important;
        font-weight: 600 !important;
    }
    button[kind="secondary"]:hover {
        background-color: #F0F4F8 !important;
    }
    
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
    
    h1, h2, h3, h4, h5, h6, p, li { color: #272838 !important; }
    .stTextInput input { border: 1px solid #815355; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "vault" not in st.session_state: st.session_state.vault = []
if "page" not in st.session_state: st.session_state.page = "Home"
if "current_report" not in st.session_state: st.session_state.current_report = ""
if "current_diet" not in st.session_state: st.session_state.current_diet = ""

# --- 4. TOP NAVIGATION BAR ---
with st.container():
    col_logo, col_nav_buttons, col_status = st.columns([3, 4, 3])
    
    with col_logo:
        if os.path.exists("medilink_logo.png"):
            st.image("medilink_logo.png", width=280)
        else:
            st.markdown("""
                <h1 style='font-family: "DM Sans", sans-serif; font-weight: 900; font-size: 50px; color: #272838 !important; margin-top: -15px; margin-bottom: 0px; line-height: 1; letter-spacing: -2px;'>MEDILINK</h1>
            """, unsafe_allow_html=True)
        
    with col_nav_buttons:
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        nav_1, nav_2, nav_3 = st.columns(3)
        with nav_1:
            if st.button("Home", use_container_width=True): st.session_state.page = "Home"
        with nav_2:
            if st.button("Trends", use_container_width=True): st.session_state.page = "Trends"
        with nav_3:
            if st.button("Files", use_container_width=True): st.session_state.page = "Files"
                
    with col_status:
        st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
        col_spacer, col_badge = st.columns([1, 2])
        with col_badge:
            st.markdown('<div class="status-badge">● Secure Connection</div>', unsafe_allow_html=True)

st.markdown("---")

# --- HELPER FUNCTIONS ---
def get_gemini_response(api_key, content, prompt):
    genai.configure(api_key=api_key)
    
    # --- SMART MODEL SELECTOR ---
    # 1. Try the Modern "Flash" Model (Best for Speed & Images)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt, content])
        return response.text
    except Exception as e_flash:
        # 2. If Flash fails (404 error), Fallback to "Pro" (Safe Mode)
        try:
            # If it's an image, we need Pro Vision
            if isinstance(content, Image.Image):
                 model = genai.GenerativeModel('gemini-pro-vision')
            # If it's text, we use Pro
            else:
                 model = genai.GenerativeModel('gemini-pro')
                 
            response = model.generate_content([prompt, content])
            return response.text
            
        except Exception as e_pro:
            st.error(f"AI Error: {str(e_pro)}")
            return None

def create_pdf(summary, action_plan):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(40, 10, 'MediLink AI Health Report')
    pdf.ln(20)
    pdf.set_font("Arial", '', 12)
    content = f"Clinical Summary:\n\n{summary}\n\nAction Plan:\n\n{action_plan}"
    try:
        content = content.encode('latin-1', 'replace').decode('latin-1')
    except:
        content = "Error encoding characters."
    pdf.multi_cell(0, 10, content)
    return pdf.output(dest='S').encode('latin-1')

def text_to_speech(text, lang_code='en'):
    try:
        if not text: return None
        tts = gTTS(text=text[:500], lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

def save_to_vault(name, type, content, summary="Pending", data=None, date=None):
    for f in st.session_state.vault:
        if f['name'] == name: 
            if summary != "Pending": f['summary'] = summary
            if data: f['data'] = data
            return
            
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

    # --- SAFE API KEY CHECK ---
    api_key = None
    try:
        if "GEMINI_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_KEY"]
    except:
        pass
    
    if not api_key:
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
                type_label = "File"
                
                if "image" in file_type:
                    uploaded_file.seek(0)
                    evidence = Image.open(uploaded_file)
                    type_label = "Image"
                    st.image(evidence, use_container_width=True)
                elif "pdf" in file_type:
                    uploaded_file.seek(0)
                    reader = PyPDF2.PdfReader(uploaded_file)
                    evidence = "".join([p.extract_text() for p in reader.pages])
                    type_label = "PDF"
                    st.info(f"{len(reader.pages)} Pages Processed")
                elif "text" in file_type:
                    uploaded_file.seek(0)
                    evidence = uploaded_file.read().decode("utf-8")
                    type_label = "Text"
                    st.text_area("Content", evidence[:200], height=150)

                save_to_vault(uploaded_file.name, type_label, evidence)

        with col2:
            st.markdown("##### Intelligence Console")
            
            lang_options = {"English": "en", "Spanish": "es", "French": "fr", "Hindi": "hi", "Chinese": "zh-CN"}
            selected_lang = st.selectbox("Output Language", list(lang_options.keys()))
            lang_code = lang_options[selected_lang]

            if uploaded_file:
                st.markdown("**Quick Options:**")
                q_col1, q_col2 = st.columns(2)
                
                with q_col1:
                    if st.button("Save & View in Files", type="secondary", use_container_width=True):
                        st.session_state.page = "Files"
                        st.rerun()

                with q_col2:
                    if st.button("Add to Trends & View", type="secondary", use_container_width=True):
                         with st.spinner("Extracting..."):
                            prompt = "Extract numerical health data. OUTPUT ONLY JSON: [{'Test':'Name', 'Value':0, 'Unit':'x'}]. If no data, return []."
                            res_text = get_gemini_response(api_key, evidence, prompt)
                            if res_text:
                                try:
                                    j_start = res_text.find("[")
                                    j_end = res_text.rfind("]") + 1
                                    data_json = json.loads(res_text[j_start:j_end])
                                    save_to_vault(uploaded_file.name, type_label, evidence, data=data_json)
                                    st.session_state.page = "Trends"
                                    st.rerun()
                                except:
                                    st.error("Failed to parse AI response.")
                
                st.markdown("---")
                
                if st.button("Run Full Diagnostics", type="primary"):
                    with st.spinner("Analyzing..."):
                        prompt = f"""
                        Act as a senior medical analyst. Language: {selected_lang}.
                        1. SUMMARY: Clear summary.
                        2. VITALS: JSON list at end: [{{'Test':'Name', 'Value':0, 'Unit':'x'}}].
                        3. ACTION PLAN: 3 lifestyle changes.
                        """
                        full_text = get_gemini_response(api_key, evidence, prompt)

                        if full_text:
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
                            save_to_vault(uploaded_file.name, type_label, evidence, summary=summary_text, data=data_json)

                if st.session_state.current_report:
                    tab_sum, tab_diet, tab_chat, tab_export = st.tabs(["Report", "Diet Plan", "Doc Talk", "Export"])
                    
                    with tab_sum:
                        st.markdown(st.session_state.current_report)
                        st.markdown("---")
                        st.caption("Audio Summary")
                        audio_file = text_to_speech(st.session_state.current_report, lang_code=lang_code[:2]) 
                        if audio_file:
                            st.audio(audio_file, format='audio/mp3')
                        if "current_data" in st.session_state and st.session_state.current_data:
                            df = pd.DataFrame(st.session_state.current_data)
                            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                            st.bar_chart(df.set_index("Test")['Value'], color="#815355")

                    with tab_diet:
                        st.markdown("##### Food is Medicine")
                        if st.button("Generate Meal Plan"):
                            with st.spinner("Cooking..."):
                                diet_prompt = f"Create a 3-day meal plan based on: {st.session_state.current_report}. Language: {selected_lang}."
                                diet_resp = get_gemini_response(api_key, "Context", diet_prompt)
                                st.session_state.current_diet = diet_resp
                        if st.session_state.current_diet:
                            st.success("Plan Created")
                            st.markdown(st.session_state.current_diet)

                    with tab_chat:
                        st.markdown("##### Ask Dr. AI")
                        user_query = st.text_input("Ask a question:")
                        if user_query:
                            with st.spinner("Thinking..."):
                                chat_prompt = f"Context: {st.session_state.current_report}. Question: {user_query}. Answer in {selected_lang}."
                                answer = get_gemini_response(api_key, "Context Provided", chat_prompt)
                                st.info(f"**AI:** {answer}")

                    with tab_export:
                        st.markdown("##### Official Download")
                        if st.button("Generate PDF Report"):
                            pdf_bytes = create_pdf(st.session_state.current_report, "See Summary for details.")
                            st.download_button("Download PDF", pdf_bytes, "medilink_report.pdf", "application/pdf")
            else:
                st.info("Awaiting file upload...")

# ================= PAGE 2: TRENDS =================
elif st.session_state.page == "Trends":
    st.markdown("### Health Trends")
    if not st.session_state.vault:
        st.info("Upload multiple reports in 'Home' to see trends here.")
    else:
        all_vitals = []
        for f in st.session_state.vault:
            if f.get('data'):
                for item in f['data']:
                    all_vitals.append({"Date": f['timestamp'], "Test": item['Test'], "Value": item['Value']})
        
        if all_vitals:
            df_trends = pd.DataFrame(all_vitals)
            df_trends['Value'] = pd.to_numeric(df_trends['Value'], errors='coerce')
            tests = df_trends['Test'].unique()
            selected_test = st.selectbox("Select Vital Sign to Track", tests)
            chart_data = df_trends[df_trends['Test'] == selected_test]
            st.line_chart(chart_data.set_index("Date")['Value'], color="#815355")
        else:
            st.warning("No numerical data found yet.")

# ================= PAGE 3: FILES =================
elif st.session_state.page == "Files":
    st.markdown("### Secure Archive")
    if not st.session_state.vault:
        st.info("No records found.")
    else:
        for i, f in enumerate(st.session_state.vault):
            with st.expander(f"{f['name']}   |   {f['timestamp']}"):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    new_name = st.text_input("Rename", f['name'], key=f"rename_{i}")
                    if new_name != f['name']:
                        f['name'] = new_name
                        st.success("Renamed")
                        st.rerun()
                with c2:
                    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                    data_to_download = None
                    file_ext, mime = "txt", "text/plain"
                    try:
                        if isinstance(f['content'], Image.Image):
                            buf = io.BytesIO()
                            f['content'].save(buf, format="PNG")
                            data_to_download, file_ext, mime = buf.getvalue(), "png", "image/png"
                        else:
                            data_to_download = str(f['content']).encode("utf-8")
                    except: pass
                    
                    if data_to_download:
                        st.download_button("Download", data_to_download, f"file_{i}.{file_ext}", mime, key=f"dl_{i}", use_container_width=True)
                
                st.markdown("---")
                if isinstance(f['content'], Image.Image): st.image(f['content'], use_container_width=True)
                else: st.text_area("Content", str(f['content']), height=150, key=f"p_{i}")
                if f['summary'] != "Pending": st.write(f['summary'])