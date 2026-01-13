import streamlit as st
import google.generativeai as genai
import json
from datetime import date
import io
import requests
import urllib.parse
import random
import re

# --- NEW LIBRARY FOR WORD DOCS ---
from docx import Document
from docx.shared import Inches, Pt, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# --- 1. CONFIGURATION & INITIALIZATION ---
st.set_page_config(page_title="DLP Generator", layout="centered")

# Initialize session state variables BEFORE they're used
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'ai_data' not in st.session_state:
    st.session_state.ai_data = None

# --- 2. FIXED SIMPLIFIED HEADER USING STREAMLIT COMPONENTS ---
def add_custom_header():
    """Add custom header with maroon background using Streamlit components only"""
    
    # Check API status safely
    api_active = st.session_state.api_key is not None
    api_status_text = "🔑 API: ACTIVE" if api_active else "⚠️ API: NOT CONFIGURED"
    api_status_color = "#d4edda" if api_active else "#fff3cd"
    api_text_color = "#155724" if api_active else "#856404"
    api_border_color = "#c3e6cb" if api_active else "#ffeaa7"
    
    # Create custom CSS for the header
    st.markdown(f"""
    <style>
    .custom-header {{
        background-color: #800000;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(128, 0, 0, 0.3);
        text-align: center;
        color: white;
    }}
    .api-status-badge {{
        display: inline-block;
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        margin-top: 10px;
        background-color: {api_status_color};
        color: {api_text_color};
        border: 1px solid {api_border_color};
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Create the header using markdown with proper HTML
    st.markdown("""
    <div class="custom-header">
        <h1 style="font-size: 24px; font-weight: bold; margin: 0; color: white;">DEPARTMENT OF EDUCATION REGION XI</h1>
        <h2 style="font-size: 20px; font-weight: bold; margin: 8px 0; color: #FFD700;">DIVISION OF DAVAO DEL SUR</h2>
        <h1 style="font-size: 28px; font-weight: bold; margin: 8px 0; color: white; text-transform: uppercase; letter-spacing: 1.5px;">MANUAL NATIONAL HIGH SCHOOL</h1>
        <p style="font-size: 15px; color: #FFD700; margin-top: 8px; font-style: italic;">Kiblawan North District</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add API status badge separately
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 10px;">
        <div class="api-status-badge">
            {api_status_text}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # App title using Streamlit component (not HTML)
    st.markdown("<h1 style='text-align: center; color: #800000; border-bottom: 3px solid #800000; padding-bottom: 10px;'>📚 AI-Powered Lesson Plan Generator</h1>", unsafe_allow_html=True)

# --- 3. ALTERNATIVE SOLUTION: USING ONLY STREAMLIT COMPONENTS ---
def add_custom_header_alternative():
    """Alternative header using only Streamlit components (no HTML)"""
    
    # Create a container with custom styling
    with st.container():
        # Department of Education
        st.markdown(
            "<h1 style='text-align: center; color: white; font-size: 24px; margin: 0;'>DEPARTMENT OF EDUCATION REGION XI</h1>",
            unsafe_allow_html=True
        )
        
        # Division
        st.markdown(
            "<h2 style='text-align: center; color: #FFD700; font-size: 20px; margin: 8px 0;'>DIVISION OF DAVAO DEL SUR</h2>",
            unsafe_allow_html=True
        )
        
        # School name
        st.markdown(
            "<h1 style='text-align: center; color: white; font-size: 28px; margin: 8px 0; text-transform: uppercase;'>MANUAL NATIONAL HIGH SCHOOL</h1>",
            unsafe_allow_html=True
        )
        
        # District
        st.markdown(
            "<p style='text-align: center; color: #FFD700; font-size: 15px; margin-top: 8px; font-style: italic;'>Kiblawan North District</p>",
            unsafe_allow_html=True
        )
    
    # API Status
    api_active = st.session_state.api_key is not None
    api_status = "🔑 API: ACTIVE" if api_active else "⚠️ API: NOT CONFIGURED"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if api_active:
            st.success(api_status)
        else:
            st.warning(api_status)
    
    # App title
    st.markdown("---")
    st.markdown("# 📚 AI-Powered Lesson Plan Generator")
    st.markdown("---")

# --- 4. SIMPLEST SOLUTION: PLAIN STREAMLIT WITH CUSTOM CSS ---
def add_custom_header_simple():
    """Simplest header solution - most reliable"""
    
    # Custom CSS for the entire header
    st.markdown("""
    <style>
    /* Main header container */
    .header-box {
        background-color: #800000;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Individual text elements */
    .dept-text {
        font-size: 24px;
        font-weight: bold;
        margin: 0;
        color: white;
    }
    
    .div-text {
        font-size: 20px;
        font-weight: bold;
        margin: 5px 0;
        color: #FFD700;
    }
    
    .school-text {
        font-size: 28px;
        font-weight: bold;
        margin: 5px 0;
        color: white;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .district-text {
        font-size: 16px;
        color: #FFD700;
        font-style: italic;
        margin-top: 8px;
    }
    
    /* API status badge */
    .api-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin-top: 10px;
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .api-badge.active {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # API status
    api_active = st.session_state.api_key is not None
    badge_class = "api-badge active" if api_active else "api-badge"
    status_text = "🔑 API: ACTIVE" if api_active else "⚠️ API: NOT CONFIGURED"
    
    # Create the header
    st.markdown(f"""
    <div class="header-box">
        <div class="dept-text">DEPARTMENT OF EDUCATION REGION XI</div>
        <div class="div-text">DIVISION OF DAVAO DEL SUR</div>
        <div class="school-text">MANUAL NATIONAL HIGH SCHOOL</div>
        <div class="district-text">Kiblawan North District</div>
        <div class="{badge_class}">{status_text}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # App title
    st.markdown("## 📚 AI-Powered Lesson Plan Generator")
    st.markdown("---")

# --- 5. API KEY SETTINGS FUNCTION ---
def api_key_settings():
    """Create settings section for API key management"""
    
    with st.sidebar.expander("⚙️ API Settings", expanded=False):
        st.markdown("### Google Gemini API Key")
        
        # Instructions
        st.markdown("""
        **Get your FREE API key:**
        1. Visit **[Google AI Studio](https://makersuite.google.com/app/apikey)**
        2. Sign in with Google
        3. Click **Create API Key**
        4. Copy and paste below
        """)
        
        # API key input
        user_api_key = st.text_input(
            "Your API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Starts with 'AIza'",
            key="api_input"
        )
        
        # Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", use_container_width=True, key="save_key"):
                if user_api_key and user_api_key.startswith("AIza"):
                    st.session_state.api_key = user_api_key.strip()
                    st.success("✅ Key saved!")
                    st.rerun()
                else:
                    st.error("❌ Invalid key format")
        with col2:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_key"):
                st.session_state.api_key = None
                st.rerun()
        
        # Current status
        if st.session_state.api_key:
            st.info(f"✅ Key configured")
        else:
            st.warning("🔑 No API key")

# --- 6. SAMPLE DATA FUNCTION ---
def create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Create sample lesson plan data"""
    topic = lesson_topic if lesson_topic else f"Introduction to {subject}"
    
    return {
        "obj_1": f"Understand {subject} concepts",
        "obj_2": f"Apply {subject} skills",
        "obj_3": f"Value {subject} in daily life",
        "topic": topic,
        "integration_within": f"Related {subject} topics",
        "integration_across": "Math & Science",
        "resources": {
            "guide": "Teacher's Guide",
            "materials": "Learner's Materials",
            "textbook": f"{subject} Textbook",
            "portal": "DepEd LR Portal",
            "other": "Online resources"
        },
        "procedure": {
            "review": "Review previous lesson",
            "purpose_situation": "Real-world application",
            "visual_prompt": "Classroom Learning",
            "vocabulary": "Term1: Definition1\nTerm2: Definition2\nTerm3: Definition3",
            "activity_main": "Group exploration activity",
            "explicitation": "Detailed explanation with examples",
            "group_1": "Research task",
            "group_2": "Problem solving",
            "group_3": "Presentation",
            "generalization": "Key learnings"
        },
        "evaluation": {
            "assess_q1": f"Question 1 about {subject}|A. Option A|B. Option B|C. Option C|D. Option D",
            "assess_q2": f"Question 2 about {subject}|A. Option A|B. Option B|C. Option C|D. Option D",
            "assess_q3": f"Question 3 about {subject}|A. Option A|B. Option B|C. Option C|D. Option D",
            "assess_q4": f"Question 4 about {subject}|A. Option A|B. Option B|C. Option C|D. Option D",
            "assess_q5": f"Question 5 about {subject}|A. Option A|B. Option B|C. Option C|D. Option D",
            "assignment": "Research assignment",
            "remarks": "Lesson delivered",
            "reflection": "Good student response"
        }
    }

# --- 7. MAIN APPLICATION ---
def main():
    # Sidebar settings
    api_key_settings()
    
    # Use the SIMPLE header function (most reliable)
    add_custom_header_simple()
    
    # Main form
    with st.form("lesson_form"):
        st.subheader("📝 Enter Lesson Details")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            subject = st.selectbox("Subject", ["Mathematics", "Science", "English", "Filipino"])
        with col2:
            grade = st.selectbox("Grade", ["7", "8", "9", "10"])
        with col3:
            quarter = st.selectbox("Quarter", ["1", "2", "3", "4"])
        
        content_std = st.text_area("Content Standard")
        perf_std = st.text_area("Performance Standard")
        competency = st.text_area("Learning Competency")
        
        # Generate button
        if st.session_state.api_key:
            btn_label = "🤖 Generate with AI"
            btn_help = "Uses Google Gemini AI"
        else:
            btn_label = "👁️ View Sample"
            btn_help = "Shows sample without API"
        
        generate_btn = st.form_submit_button(
            btn_label,
            help=btn_help,
            type="primary"
        )
    
    # Handle generation
    if generate_btn:
        with st.spinner("Creating lesson plan..."):
            ai_data = create_sample_data(subject, grade, quarter, content_std, perf_std, competency)
            st.session_state.ai_data = ai_data
            st.session_state.generated = True
        
        st.success("✅ Lesson plan created!")
        
        # Display results
        st.subheader("📄 Generated Lesson Plan")
        st.json(ai_data)

# --- 8. RUN APP ---
if __name__ == "__main__":
    main()
