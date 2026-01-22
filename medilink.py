import streamlit as st
import PyPDF2
from google import genai
from PIL import Image
import pandas as pd
import json
import io

# --- 1. PROFESSIONAL PAGE CONFIG ---
st.set_page_config(
    page_title="MediLink Pro",
    page_icon="🩺",
    layout="wide", # This makes it look like a dashboard
    initial_sidebar_state="expanded"
)

# Custom CSS to make it look cleaner (removes standard Streamlit padding)
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
    st.caption("v2.0 | Ivy League Build")
    st.divider()
    
    uploaded_file = st.file_uploader("Upload Medical Record", type=['pdf', 'jpg', 'png', 'txt'])
    
    # Secure Key Logic
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("🔒 Secure Connection Active")
    else:
        api_key = st.text_input("API Key", type="password")
        st.caption("Enterprise Grade Security")

# --- MAIN DASHBOARD LOGIC ---
if uploaded_file and api_key:
    # Prepare the layout: 2 Columns
    col1, col2 = st.columns([1, 1.5], gap="large")

    # --- LEFT COLUMN: THE DOCUMENT ---
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

    # --- RIGHT COLUMN: THE INTELLIGENCE ---
    with col2:
        st.subheader("🧠 AI Diagnostics")
        
        if st.button("Analyze Report", type="primary"):
            client = genai.Client(api_key=api_key)
            
            with st.spinner("Processing medical data..."):
                try:
                    # PRO TRICK: We ask for TWO things in one prompt:
                    # 1. A summary
                    # 2. A specific JSON data block for charts
                    prompt = """
                    You are an expert medical analyst. Analyze the provided document.
                    
                    TASK 1: SUMMARY
                    Provide a professional summary of the patient's status in plain English.
                    
                    TASK 2: DATA EXTRACTION
                    Extract any numerical test results (like Cholesterol, Glucose, Iron).
                    Format them strictly as a JSON list at the VERY END of your response.
                    Example format:
                    [
                        {"Test": "Total Cholesterol", "Value": 180, "Unit": "mg/dL"},
                        {"Test": "LDL", "Value": 100, "Unit": "mg/dL"}
                    ]
                    
                    If no numbers are found, return an empty JSON [].
                    Do not use markdown formatting (```json) for the JSON part, just raw text at the end.
                    """
                    
                    response = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=[evidence_for_ai, prompt]
                    )
                    
                    # Split response into Text vs Data
                    # This is a simple parser assuming JSON is at the end
                    full_text = response.text
                    try:
                        # Find the start of the JSON list
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
                    
                    # 2. Display Charts (The "Visualizer")
                    if data_json:
                        st.divider()
                        st.markdown("### 📊 Vitals Visualization")
                        df = pd.DataFrame(data_json)
                        
                        # Display as a clean table
                        st.dataframe(df, hide_index=True, use_container_width=True)
                        
                        # Display as a Bar Chart
                        # We try to clean the 'Value' column to ensure it's numbers
                        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                        st.bar_chart(df.set_index("Test")['Value'])
                    else:
                        st.info("No numerical data detected for visualization.")

                except Exception as e:
                    st.error(f"Analysis Error: {e}")

else:
    # --- LANDING PAGE (Empty State) ---
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