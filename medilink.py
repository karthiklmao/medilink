import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import time

# --- 1. PROFESSIONAL PAGE CONFIG ---
st.set_page_config(
    page_title="MediLink Pro",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .main { padding-top: 2rem; }
    div.stButton > button:first-child { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (CONTROLS) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
    st.title("MediLink Portal")
    st.caption("v2.1 | Ivy League Build")
    st.divider()
    
    uploaded_file = st.file_uploader("Upload Medical Record", type=['pdf', 'jpg', 'jpeg', 'png', 'txt'])
    
    # Secure Key Logic
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("🔒 Secure Connection Active")
    else:
        api_key = st.text_input("Enter API Key", type="password")
        st.caption("Enterprise Grade Security")

# --- HELPER FUNCTION: RETRY LOGIC (CRASH PROTECTION) ---
def get_gemini_response(client, content, prompt):
    """Tries to call AI. If rate limited (429), waits and retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[content, prompt]
            )
        except Exception as e:
            # Check if error is related to Rate Limit (429)
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (attempt + 1) * 5  # Wait 5s, then 10s...
                st.warning(f"⚠️ High traffic (Rate Limit). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e  # If it's a real error (like bad key), crash properly
    raise Exception("Server is too busy. Please try again in a minute.")

# --- MAIN DASHBOARD LOGIC ---
if uploaded_file and api_key:
    # Layout: 2 Columns (Document vs Analysis)
    col1, col2 = st.columns([1, 1.5], gap="large")

    # --- LEFT COLUMN: DOCUMENT VIEWER ---
    with col1:
        st.subheader("📄 Document Viewer")
        file_type = uploaded_file.type
        evidence_for_ai = None

        if "pdf" in file_type:
            uploaded_file.seek(0)
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            evidence_for_ai = text
            st.info(f"PDF Loaded: {len(reader.pages)} pages detected.")
            with st.expander("Preview Raw Text"):
                st.text(text[:800] + "...")

        elif "image" in file_type:
            uploaded_file.seek(0)
            evidence_for_ai = Image.open(uploaded_file)
            st.image(evidence_for_ai, use_container_width=True, caption="Scanned Document")
            
        elif "text" in file_type:
            uploaded_file.seek(0)
            evidence_for_ai = uploaded_file.read().decode("utf-8")
            st.text_area("File Content", evidence_for_ai, height=300)

    # --- RIGHT COLUMN: AI INTELLIGENCE ---
    with col2:
        st.subheader("🧠 AI Diagnostics")
        
        if st.button("Analyze Report", type="primary"):
            client = genai.Client(api_key=api_key)
            
            with st.spinner("Processing medical data (this may take a moment)..."):
                try:
                    # PROMPTING: Ask for Summary + JSON Data
                    prompt = """
                    You are an expert medical analyst. Analyze the provided document.
                    
                    TASK 1: SUMMARY
                    Provide a professional summary of the patient's status in plain English.
                    
                    TASK 2: DATA EXTRACTION
                    Extract any numerical test results (like Cholesterol, Glucose, Iron, RBC, etc).
                    Format them strictly as a JSON list at the VERY END of your response.
                    Example format:
                    [
                        {"Test": "Total Cholesterol", "Value": 180, "Unit": "mg/dL"},
                        {"Test": "LDL", "Value": 100, "Unit": "mg/dL"}
                    ]
                    
                    If no numbers are found, return an empty JSON [].
                    Do not use markdown formatting (```json) for the JSON part, just raw text at the end.
                    """
                    
                    # CALL WITH RETRY LOGIC
                    response = get_gemini_response(client, evidence_for_ai, prompt)
                    
                    # PARSING: Split Text from JSON
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

                    # 1. Display Summary
                    st.markdown("### 📋 Clinical Summary")
                    st.markdown(summary)
                    
                    # 2. Display Charts (The Visualizer)
                    if data_json:
                        st.divider()
                        st.markdown("### 📊 Vitals Visualization")
                        df = pd.DataFrame(data_json)
                        
                        # Clean Data for Charting
                        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                        
                        # Show Table
                        st.dataframe(df, hide_index=True, use_container_width=True)
                        
                        # Show Chart
                        st.bar_chart(df.set_index("Test")['Value'])
                    else:
                        st.info("No numerical data detected for visualization.")
                        
                    # 3. Download Button
                    st.download_button(
                        label="📥 Download Report",
                        data=full_text,
                        file_name="medilink_analysis.txt"
                    )

                except Exception as e:
                    st.error(f"Analysis Error: {e}")

else:
    # --- LANDING PAGE ---
    st.title("Welcome to MediLink Pro")
    st.markdown("""
    ### Secure Medical Analysis Platform
    Upload your medical records to generate:
    * **Clinical Summaries**
    * **Trend Visualizations**
    * **Plain English Explanations**
    
    *Powered by Gemini 2.0 Flash*
    """)
    st.info("👈 Upload a file in the sidebar to begin.")