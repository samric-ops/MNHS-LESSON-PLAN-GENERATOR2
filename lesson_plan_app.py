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

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DLP Generator", layout="centered")

# --- 2. SIDEBAR SETTINGS FOR API KEY ---
def api_key_settings():
    """Create settings section for API key management"""
    
    with st.sidebar.expander("⚙️ API Settings", expanded=False):
        st.markdown("### Google Gemini API Key Setup")
        
        # Instruction section with tutorial link
        st.markdown("""
        **How to get your FREE API key:**
        1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with your Google account
        3. Click **"Get API Key"** → **"Create API Key"**
        4. Copy your key and paste it below
        5. Your key is stored only in your browser
        """)
        
        # Clickable link button
        if st.button("🔗 Go to Google AI Studio to Get Free API Key", use_container_width=True):
            st.markdown('<meta http-equiv="refresh" content="0; url=https://makersuite.google.com/app/apikey">', unsafe_allow_html=True)
        
        # API key input with password masking
        user_api_key = st.text_input(
            "Enter your Google Gemini API Key:",
            type="password",
            placeholder="AIzaSyD...",
            help="Paste your API key from Google AI Studio here"
        )
        
        # Initialize session state for API key
        if 'api_key' not in st.session_state:
            st.session_state.api_key = None
        
        # Save button for API key
        if st.button("💾 Save API Key", use_container_width=True):
            if user_api_key and user_api_key.startswith("AIza"):
                st.session_state.api_key = user_api_key
                st.success("✅ API Key saved successfully!")
                st.rerun()
            elif user_api_key:
                st.error("⚠️ Please enter a valid API key starting with 'AIza'")
            else:
                st.error("⚠️ Please enter your API key")
        
        # Show status
        if st.session_state.api_key:
            st.info("🔑 API Key: **Configured** (starts with: " + st.session_state.api_key[:10] + "***)")
            
            # Option to clear API key
            if st.button("🗑️ Clear API Key", use_container_width=True, type="secondary"):
                st.session_state.api_key = None
                st.rerun()
        else:
            st.warning("⚠️ No API key configured. Get one from the link above.")
        
        st.divider()
        
        # Quick test button
        if st.session_state.api_key:
            if st.button("🧪 Test API Connection", use_container_width=True):
                with st.spinner("Testing connection..."):
                    try:
                        genai.configure(api_key=st.session_state.api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content("Hello")
                        st.success("✅ API connection successful!")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
                        st.info("Please check your API key and try again.")

# --- 3. API KEY MANAGEMENT FUNCTION ---
def get_api_key():
    """Get the API key from session state or prompt user"""
    
    # Check if API key exists in session state
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    
    # If no API key, show warning and instructions
    if not st.session_state.api_key:
        st.warning("""
        ⚠️ **API Key Required**
        
        Please configure your Google Gemini API key in the ⚙️ **API Settings** sidebar.
        
        1. Click on ⚙️ **API Settings** in the sidebar
        2. Get a FREE key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        3. Paste it in the input box
        4. Click "Save API Key"
        
        Without an API key, you can only view sample lesson plans.
        """)
        
        # Create a sample data button for demonstration
        if st.button("👁️ View Sample Lesson Plan (No API Required)", use_container_width=True):
            return "SAMPLE_MODE"
        
        return None
    
    return st.session_state.api_key

# --- 4. SIMPLIFIED HEADER WITHOUT LOGOS ---
def add_custom_header():
    """Add custom header with maroon background (NO LOGOS)"""
    
    st.markdown("""
    <style>
    .header-container {
        text-align: center;
        padding: 20px;
        margin-bottom: 25px;
        background-color: #800000; /* MAROON BACKGROUND */
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(128, 0, 0, 0.3);
        color: white;
    }
    .dept-name {
        font-size: 24px;
        font-weight: bold;
        color: white;
        margin: 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    .division-name {
        font-size: 20px;
        font-weight: bold;
        color: #FFD700; /* Gold color for contrast */
        margin: 8px 0;
    }
    .school-name {
        font-size: 28px;
        font-weight: bold;
        color: white;
        margin: 8px 0;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .header-subtext {
        font-size: 15px;
        color: #FFD700; /* Gold color */
        margin-top: 8px;
        font-style: italic;
    }
    
    /* App title styling */
    .app-title {
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        color: #800000; /* Maroon */
        margin: 15px 0 25px 0;
        padding: 10px;
        border-bottom: 3px solid #800000;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    /* API status indicator */
    .api-status {
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
    }
    .api-active {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .api-inactive {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    </style>
    
    <div class="header-container">
        <p class="dept-name">DEPARTMENT OF EDUCATION REGION XI</p>
        <p class="division-name">DIVISION OF DAVAO DEL SUR</p>
        <p class="school-name">MANUAL NATIONAL HIGH SCHOOL</p>
        <p class="header-subtext">Kiblawan North District</p>
        
        <!-- API Status Indicator -->
        <div class="api-status {api_status_class}">
            {api_status_text}
        </div>
    </div>
    """.format(
        api_status_class="api-active" if st.session_state.get('api_key') else "api-inactive",
        api_status_text="🔑 API: ACTIVE" if st.session_state.get('api_key') else "⚠️ API: NOT CONFIGURED"
    ), unsafe_allow_html=True)
    
    # App title
    st.markdown('<p class="app-title">📚 AI-Powered Lesson Plan Generator</p>', unsafe_allow_html=True)

# --- 5. MODIFIED AI GENERATOR FUNCTION ---
def generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency, 
                           obj_cognitive=None, obj_psychomotor=None, obj_affective=None,
                           lesson_topic=None):
    try:
        # Get API key from session state
        api_key = get_api_key()
        
        # If no API key and not in sample mode, return None
        if not api_key:
            return None
        
        # If in sample mode, return sample data
        if api_key == "SAMPLE_MODE":
            return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
        # Configure with user's API key
        genai.configure(api_key=api_key)
        
        # Try multiple model options
        model_options = ['gemini-2.0-flash-exp', 'gemini-1.5-flash', 'gemini-1.5-pro']
        model = None
        
        for model_name in model_options:
            try:
                model = genai.GenerativeModel(model_name)
                # Test with a simple prompt
                test_response = model.generate_content("Hello")
                if test_response:
                    st.sidebar.success(f"✓ Using model: {model_name}")
                    break
            except Exception as e:
                continue
        
        if not model:
            # Fallback to default
            model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Check if user provided objectives
        user_provided_objectives = obj_cognitive and obj_psychomotor and obj_affective
        
        # Check if user provided topic (optional)
        user_provided_topic = lesson_topic and lesson_topic.strip()
        
        if user_provided_objectives or user_provided_topic:
            # Build prompt with user-provided content
            prompt_parts = [
                f"""You are an expert teacher from Manual National High School in the Division of Davao Del Sur, Region XI, Philippines.
                Create a JSON object for a Daily Lesson Plan (DLP).
                Subject: {subject}, Grade: {grade}, Quarter: {quarter}
                Content Standard: {content_std}
                Performance Standard: {perf_std}
                Learning Competency: {competency}"""]

            if user_provided_objectives:
                prompt_parts.append(f"""
                USER-PROVIDED OBJECTIVES:
                - Cognitive: {obj_cognitive}
                - Psychomotor: {obj_psychomotor}
                - Affective: {obj_affective}
                IMPORTANT: Use these exact objectives provided by the user. Do NOT modify them.""")

            if user_provided_topic:
                prompt_parts.append(f"""
                USER-PROVIDED LESSON TOPIC/CONTENT:
                {lesson_topic}
                IMPORTANT: Use this exact topic/content provided by the user. Do NOT modify it.""")

            prompt_parts.append(f"""
            CRITICAL INSTRUCTIONS:
            1. You MUST generate exactly 5 distinct MULTIPLE CHOICE assessment questions with A, B, C, D choices.
            2. Each assessment question MUST follow this format: "question|A. choice1|B. choice2|C. choice3|D. choice4"
            3. The correct answer should be included in the choices.
            4. Return ONLY valid JSON format.
            5. Do NOT use bullet points (•) or any markdown in the JSON values.
            6. All string values must be properly quoted.
            7. Do NOT include any explanations outside the JSON.

            Return ONLY raw JSON. No markdown formatting.
            Structure:
            {{
                "obj_1": "Cognitive objective",
                "obj_2": "Psychomotor objective",
                "obj_3": "Affective objective",
                "topic": "The main topic (include math equations like 3x^2 if needed)",
                "integration_within": "Topic within same subject",
                "integration_across": "Topic across other subject",
                "resources": {{
                    "guide": "Teacher Guide reference",
                    "materials": "Learner Materials reference",
                    "textbook": "Textbook reference",
                    "portal": "Learning Resource Portal reference",
                    "other": "Other Learning Resources"
                }},
                "procedure": {{
                    "review": "Review activity",
                    "purpose_situation": "Real-life situation motivation description",
                    "visual_prompt": "A simple 3-word visual description. Example: 'Red Apple Fruit'. NO sentences.",
                    "vocabulary": "5 terms with definitions",
                    "activity_main": "Main activity description",
                    "explicitation": "Detailed explanation of the concept with clear explanations and TWO specific examples with detailed explanations",
                    "group_1": "Group 1 task",
                    "group_2": "Group 2 task",
                    "group_3": "Group 3 task",
                    "generalization": "Reflection questions"
                }},
                "evaluation": {{
                    "assess_q1": "Question 1 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q2": "Question 2 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q3": "Question 3 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q4": "Question 4 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q5": "Question 5 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assignment": "Assignment task",
                    "remarks": "Remarks",
                    "reflection": "Reflection"
                }}
            }}
            """)
            
            prompt = "\n".join(prompt_parts)
        else:
            # Generate everything automatically
            prompt = f"""
            You are an expert teacher from Manual National High School in the Division of Davao Del Sur, Region XI, Philippines.
            Create a JSON object for a Daily Lesson Plan (DLP).
            Subject: {subject}, Grade: {grade}, Quarter: {quarter}
            Content Standard: {content_std}
            Performance Standard: {perf_std}
            Learning Competency: {competency}

            CRITICAL INSTRUCTIONS:
            1. You MUST generate exactly 5 distinct MULTIPLE CHOICE assessment questions with A, B, C, D choices.
            2. Each assessment question MUST follow this format: "question|A. choice1|B. choice2|C. choice3|D. choice4"
            3. The correct answer should be included in the choices.
            4. Return ONLY valid JSON format.
            5. Do NOT use bullet points (•) or any markdown in the JSON values.
            6. All string values must be properly quoted.
            7. Do NOT include any explanations outside the JSON.

            Return ONLY raw JSON. No markdown formatting.
            Structure:
            {{
                "obj_1": "Cognitive objective",
                "obj_2": "Psychomotor objective",
                "obj_3": "Affective objective",
                "topic": "The main topic (include math equations like 3x^2 if needed)",
                "integration_within": "Topic within same subject",
                "integration_across": "Topic across other subject",
                "resources": {{
                    "guide": "Teacher Guide reference",
                    "materials": "Learner Materials reference",
                    "textbook": "Textbook reference",
                    "portal": "Learning Resource Portal reference",
                    "other": "Other Learning Resources"
                }},
                "procedure": {{
                    "review": "Review activity",
                    "purpose_situation": "Real-life situation motivation description",
                    "visual_prompt": "A simple 3-word visual description. Example: 'Red Apple Fruit'. NO sentences.",
                    "vocabulary": "5 terms with definitions",
                    "activity_main": "Main activity description",
                    "explicitation": "Detailed explanation of the concept with clear explanations and TWO specific examples with detailed explanations",
                    "group_1": "Group 1 task",
                    "group_2": "Group 2 task",
                    "group_3": "Group 3 task",
                    "generalization": "Reflection questions"
                }},
                "evaluation": {{
                    "assess_q1": "Question 1 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q2": "Question 2 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q3": "Question 3 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q4": "Question 4 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assess_q5": "Question 5 with choices in format: question|A. choice1|B. choice2|C. choice3|D. choice4",
                    "assignment": "Assignment task",
                    "remarks": "Remarks",
                    "reflection": "Reflection"
                }}
            }}
            """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Clean the JSON response
        cleaned_text = clean_json_string(text)
        
        # Log for debugging
        st.sidebar.text_area("Raw AI Response", cleaned_text[:1000], height=200)
        
        # Try to parse the JSON
        try:
            ai_data = json.loads(cleaned_text)
            
            # If user provided topic but AI didn't use it, override
            if user_provided_topic and 'topic' in ai_data:
                ai_data['topic'] = lesson_topic
                
            return ai_data
        except json.JSONDecodeError as je:
            st.error(f"JSON Parsing Error: {je}")
            st.sidebar.error("Failed to parse JSON. Attempting manual fix...")
            
            # Attempt manual extraction
            try:
                # Try to extract JSON using regex
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, cleaned_text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    # Remove any trailing commas
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    ai_data = json.loads(json_str)
                    
                    # If user provided topic but AI didn't use it, override
                    if user_provided_topic and 'topic' in ai_data:
                        ai_data['topic'] = lesson_topic
                        
                    return ai_data
            except Exception as e2:
                st.error(f"Manual JSON extraction also failed: {e2}")
                # Create fallback data
                return create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
    except Exception as e:
        st.error(f"AI Generation Error: {str(e)}")
        # Create fallback data
        return create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)

def create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Create sample data for demonstration without API key"""
    topic = lesson_topic if lesson_topic else f"Sample: Introduction to {subject}"
    
    return {
        "obj_1": f"Understand basic {subject} concepts (Sample)",
        "obj_2": f"Apply {subject} skills in simple exercises (Sample)",
        "obj_3": f"Appreciate the value of learning {subject} (Sample)",
        "topic": topic,
        "integration_within": f"Related {subject} topics (Sample)",
        "integration_across": "Mathematics, Science (Sample Integration)",
        "resources": {
            "guide": "Teacher's Guide (Sample)",
            "materials": "Learner's Materials (Sample)",
            "textbook": f"{subject} Textbook - Chapter 1 (Sample)",
            "portal": "DepEd LR Portal - Sample Resources",
            "other": "Online educational websites (Sample)"
        },
        "procedure": {
            "review": "Review of previous lesson on basic concepts (Sample)",
            "purpose_situation": f"Real-world application of {subject} in daily life (Sample)",
            "visual_prompt": f"{subject} Classroom Learning",
            "vocabulary": f"{subject}: The study of...\nTerm1: Definition1\nTerm2: Definition2\nTerm3: Definition3\nTerm4: Definition4\nTerm5: Definition5",
            "activity_main": f"Group activity exploring {subject} concepts (Sample)",
            "explicitation": f"Detailed explanation of {subject} with examples. Example 1: Basic application. Example 2: Advanced application. (Sample)",
            "group_1": "Research and gather information (Sample)",
            "group_2": "Solve practice problems (Sample)",
            "group_3": "Create a presentation (Sample)",
            "generalization": "What key concepts did you learn today? How can you apply them?"
        },
        "evaluation": {
            "assess_q1": f"What is the main concept of {subject}?|A. Concept A (Correct)|B. Concept B|C. Concept C|D. Concept D",
            "assess_q2": f"How would you apply {subject} in real life?|A. Application A|B. Application B (Correct)|C. Application C|D. Application D",
            "assess_q3": f"Explain the difference between key terms in {subject}.|A. Difference A|B. Difference B|C. Difference C (Correct)|D. Difference D",
            "assess_q4": f"Solve a simple problem using {subject} concepts.|A. Solution A|B. Solution B|C. Solution C|D. Solution D (Correct)",
            "assess_q5": f"What are the limitations of {subject} approaches?|A. Limitation A (Correct)|B. Limitation B|C. Limitation C|D. Limitation D",
            "assignment": "Research more about the topic online (Sample)",
            "remarks": "Sample lesson plan - Configure API for full functionality",
            "reflection": "Students demonstrated understanding of sample concepts"
        }
    }

# [The rest of your existing functions remain the same: clean_json_string, fetch_ai_image, and all the docx functions]

# --- 6. MAIN APPLICATION LOGIC ---
def main():
    # Add API settings to sidebar
    api_key_settings()
    
    # Add custom header
    add_custom_header()
    
    # Get API key status
    api_key = get_api_key()
    
    # If no API key and user didn't choose sample mode, show instructions
    if not api_key:
        st.info("💡 **Tip**: You can still explore the app interface below. Enter your lesson details and try the 'View Sample' option to see how it works.")
    
    # Rest of your existing main form and application logic goes here
    # [Your existing form inputs, generate button, and display logic]
    
    # Example form section (simplified)
    with st.form("lesson_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            subject = st.selectbox("Subject Area", ["Mathematics", "Science", "English", "Filipino", "Araling Panlipunan"])
        with col2:
            grade = st.selectbox("Grade Level", ["7", "8", "9", "10", "11", "12"])
        with col3:
            quarter = st.selectbox("Quarter", ["1", "2", "3", "4"])
        
        content_std = st.text_area("Content Standard")
        perf_std = st.text_area("Performance Standard")
        competency = st.text_area("Learning Competency")
        
        # Add a note about API requirement
        if not api_key or api_key == "SAMPLE_MODE":
            generate_button = st.form_submit_button("👁️ View Sample Lesson Plan", 
                help="Generate a sample lesson plan without API key")
            mode = "sample"
        else:
            generate_button = st.form_submit_button("🤖 Generate AI Lesson Plan",
                help="Generate a full AI-powered lesson plan using your API key")
            mode = "ai"
        
        if generate_button:
            if mode == "sample":
                ai_data = create_sample_data(subject, grade, quarter, content_std, perf_std, competency)
                st.session_state.ai_data = ai_data
                st.session_state.generated = True
                st.success("✅ Sample lesson plan generated! Configure API for AI-powered generation.")
            else:
                with st.spinner("🤖 AI is generating your lesson plan..."):
                    ai_data = generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency)
                    if ai_data:
                        st.session_state.ai_data = ai_data
                        st.session_state.generated = True
                        st.success("✅ AI lesson plan generated successfully!")

# --- 7. RUN THE APPLICATION ---
if __name__ == "__main__":
    main()
