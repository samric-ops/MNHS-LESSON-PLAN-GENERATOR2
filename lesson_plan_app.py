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

# --- 2. FIXED SIMPLIFIED HEADER FUNCTION ---
def add_custom_header():
    """Add custom header with maroon background (NO LOGOS) - FIXED VERSION"""
    
    # Check API status safely
    api_status_class = "api-active" if st.session_state.api_key else "api-inactive"
    api_status_text = "🔑 API: ACTIVE" if st.session_state.api_key else "⚠️ API: NOT CONFIGURED"
    
    st.markdown(f"""
    <style>
    .header-container {{
        text-align: center;
        padding: 20px;
        margin-bottom: 25px;
        background-color: #800000; /* MAROON BACKGROUND */
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(128, 0, 0, 0.3);
        color: white;
    }}
    .dept-name {{
        font-size: 24px;
        font-weight: bold;
        color: white;
        margin: 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }}
    .division-name {{
        font-size: 20px;
        font-weight: bold;
        color: #FFD700; /* Gold color for contrast */
        margin: 8px 0;
    }}
    .school-name {{
        font-size: 28px;
        font-weight: bold;
        color: white;
        margin: 8px 0;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }}
    .header-subtext {{
        font-size: 15px;
        color: #FFD700; /* Gold color */
        margin-top: 8px;
        font-style: italic;
    }}
    
    /* App title styling */
    .app-title {{
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        color: #800000; /* Maroon */
        margin: 15px 0 25px 0;
        padding: 10px;
        border-bottom: 3px solid #800000;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }}
    
    /* API status indicator */
    .api-status {{
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
    }}
    .api-active {{
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }}
    .api-inactive {{
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }}
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
    
    <p class="app-title">📚 AI-Powered Lesson Plan Generator</p>
    """, unsafe_allow_html=True)

# --- 3. FIXED API KEY SETTINGS FUNCTION ---
def api_key_settings():
    """Create settings section for API key management - FIXED VERSION"""
    
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
        if st.button("🔗 Go to Google AI Studio to Get Free API Key", 
                    key="go_to_ai_studio", 
                    use_container_width=True):
            # Open in new tab using JavaScript
            js = """
            <script>
            window.open("https://makersuite.google.com/app/apikey", "_blank");
            </script>
            """
            st.components.v1.html(js, height=0)
        
        # API key input with password masking
        user_api_key = st.text_input(
            "Enter your Google Gemini API Key:",
            type="password",
            placeholder="AIzaSyD...",
            help="Paste your API key from Google AI Studio here",
            key="api_key_input"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Save button for API key
            if st.button("💾 Save API Key", use_container_width=True, key="save_api_key"):
                if user_api_key and user_api_key.strip():
                    if user_api_key.startswith("AIza"):
                        st.session_state.api_key = user_api_key.strip()
                        st.success("✅ API Key saved successfully!")
                        st.rerun()
                    else:
                        st.error("⚠️ Please enter a valid API key starting with 'AIza'")
                else:
                    st.error("⚠️ Please enter your API key")
        
        with col2:
            # Option to clear API key
            if st.button("🗑️ Clear API Key", 
                        use_container_width=True, 
                        type="secondary",
                        key="clear_api_key"):
                st.session_state.api_key = None
                st.rerun()
        
        # Show status
        if st.session_state.api_key:
            masked_key = st.session_state.api_key[:10] + "***" + st.session_state.api_key[-4:]
            st.info(f"🔑 API Key: **Configured** ({masked_key})")
        else:
            st.warning("⚠️ No API key configured. Get one from the link above.")
        
        st.divider()
        
        # Quick test button
        if st.session_state.api_key:
            if st.button("🧪 Test API Connection", 
                        use_container_width=True, 
                        key="test_api_connection"):
                with st.spinner("Testing connection..."):
                    try:
                        genai.configure(api_key=st.session_state.api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content("Hello")
                        if response and response.text:
                            st.success("✅ API connection successful!")
                        else:
                            st.error("❌ API returned empty response")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)[:100]}")
                        st.info("Please check your API key and try again.")

# --- 4. FIXED API KEY MANAGEMENT FUNCTION ---
def get_api_key():
    """Get the API key from session state or prompt user - FIXED VERSION"""
    
    # Check if API key exists
    if not st.session_state.api_key:
        # Create a container for the warning
        warning_container = st.container()
        
        with warning_container:
            st.warning("""
            ⚠️ **API Key Required**
            
            Please configure your Google Gemini API key in the ⚙️ **API Settings** sidebar.
            
            1. Click on ⚙️ **API Settings** in the sidebar
            2. Get a FREE key from [Google AI Studio](https://makersuite.google.com/app/apikey)
            3. Paste it in the input box
            4. Click "Save API Key"
            
            Without an API key, you can only view sample lesson plans.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                # Create a sample data button for demonstration
                if st.button("👁️ View Sample Lesson Plan", 
                           use_container_width=True,
                           key="view_sample"):
                    return "SAMPLE_MODE"
            with col2:
                if st.button("⚙️ Open API Settings", 
                           use_container_width=True,
                           key="open_settings"):
                    # This will trigger a rerun with settings expanded
                    st.session_state.get('settings_expanded', True)
        
        return None
    
    return st.session_state.api_key

# --- 5. FIXED SAMPLE DATA FUNCTION ---
def create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Create sample data for demonstration without API key - FIXED VERSION"""
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

# --- 6. FIXED CLEAN JSON FUNCTION ---
def clean_json_string(json_string):
    """Clean the JSON string by removing invalid characters and fixing common issues - FIXED VERSION"""
    if not json_string:
        return json_string
    
    # Remove markdown code blocks
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'```\s*', '', json_string)
    
    # Remove bullet points and other invalid characters
    json_string = json_string.replace('•', '-')  # Replace bullet points with hyphens
    json_string = json_string.replace('\u2022', '-')  # Unicode bullet
    json_string = json_string.replace('\u25cf', '-')  # Black circle bullet
    
    # Fix truncated strings (add closing quotes)
    json_string = re.sub(r':\s*$', '": ""', json_string)  # Fix truncated values at end of line
    
    # Fix unclosed quotes in the middle of JSON
    lines = json_string.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        # Count quotes in the line
        quote_count = line.count('"')
        
        # If odd number of quotes, add a closing quote at the end
        if quote_count % 2 == 1 and ':' in line:
            # Find the last colon position
            last_colon_pos = line.rfind(':')
            if last_colon_pos > 0:
                # Check if there's an opening quote after the colon
                after_colon = line[last_colon_pos + 1:].strip()
                if after_colon.startswith('"') and not after_colon.endswith('"'):
                    line = line + '"'
                elif not after_colon.startswith('"') and after_colon:
                    # If value doesn't start with quote but should be string
                    value_start = last_colon_pos + 1
                    while value_start < len(line) and line[value_start] in ' \t':
                        value_start += 1
                    if value_start < len(line):
                        line = line[:value_start] + '"' + line[value_start:] + '"'
    
        cleaned_lines.append(line)
    
    json_string = '\n'.join(cleaned_lines)
    
    # Remove any control characters except newlines and tabs
    json_string = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_string)
    
    # Fix common JSON issues
    json_string = re.sub(r',\s*}', '}', json_string)  # Remove trailing commas before }
    json_string = re.sub(r',\s*]', ']', json_string)  # Remove trailing commas before ]
    
    return json_string

# --- 7. FIXED AI GENERATOR FUNCTION ---
def generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency, 
                           obj_cognitive=None, obj_psychomotor=None, obj_affective=None,
                           lesson_topic=None):
    try:
        # Get API key from session state
        api_key = st.session_state.api_key
        
        # If no API key, return sample data
        if not api_key:
            return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
        # Configure with user's API key
        genai.configure(api_key=api_key)
        
        # Try multiple model options
        model_options = ['gemini-1.5-flash', 'gemini-1.5-pro']
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
        
        # Build prompt
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
        
        # Try to parse the JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # If parsing fails, return sample data
            st.error("AI response parsing failed. Showing sample data instead.")
            return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
    except Exception as e:
        st.error(f"AI Generation Error: {str(e)}")
        # Return sample data on error
        return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)

# --- 8. FIXED MAIN APPLICATION LOGIC ---
def main():
    # Add API settings to sidebar FIRST
    api_key_settings()
    
    # Add custom header
    add_custom_header()
    
    # Main form for lesson plan generation
    with st.form("lesson_form", clear_on_submit=False):
        st.subheader("📝 Lesson Plan Details")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            subject = st.selectbox("Subject Area", 
                                 ["Mathematics", "Science", "English", "Filipino", "Araling Panlipunan", "MAPEH", "ESP", "TLE"])
        with col2:
            grade = st.selectbox("Grade Level", ["7", "8", "9", "10", "11", "12"])
        with col3:
            quarter = st.selectbox("Quarter", ["1", "2", "3", "4"])
        
        content_std = st.text_area("Content Standard", 
                                 placeholder="E.g., The learner demonstrates understanding of...")
        perf_std = st.text_area("Performance Standard", 
                              placeholder="E.g., The learner is able to...")
        competency = st.text_area("Learning Competency", 
                                placeholder="E.g., Differentiates between...")
        
        # Optional custom objectives
        with st.expander("➕ Custom Objectives (Optional)"):
            col_obj1, col_obj2, col_obj3 = st.columns(3)
            with col_obj1:
                obj_cognitive = st.text_input("Cognitive Objective", 
                                            placeholder="E.g., Analyze the concept of...")
            with col_obj2:
                obj_psychomotor = st.text_input("Psychomotor Objective", 
                                              placeholder="E.g., Create a model showing...")
            with col_obj3:
                obj_affective = st.text_input("Affective Objective", 
                                            placeholder="E.g., Appreciate the importance of...")
        
        lesson_topic = st.text_input("Lesson Topic (Optional)", 
                                   placeholder="E.g., Photosynthesis, Quadratic Equations...")
        
        # Generate button with conditional text
        if st.session_state.api_key:
            generate_text = "🤖 Generate AI Lesson Plan"
            generate_help = "Generate using Google Gemini AI"
        else:
            generate_text = "👁️ View Sample Lesson Plan"
            generate_help = "View a sample without API key"
        
        generate_button = st.form_submit_button(
            generate_text,
            help=generate_help,
            type="primary",
            use_container_width=True
        )
    
    # Handle form submission
    if generate_button:
        with st.spinner("Generating your lesson plan..."):
            if st.session_state.api_key:
                # Generate with AI
                ai_data = generate_lesson_content(
                    subject, grade, quarter, content_std, perf_std, competency,
                    obj_cognitive, obj_psychomotor, obj_affective, lesson_topic
                )
            else:
                # Generate sample data
                ai_data = create_sample_data(
                    subject, grade, quarter, content_std, perf_std, competency, lesson_topic
                )
            
            if ai_data:
                st.session_state.ai_data = ai_data
                st.session_state.generated = True
                st.success("✅ Lesson plan generated successfully!")
                st.rerun()
    
    # Display generated lesson plan
    if st.session_state.get('generated') and st.session_state.get('ai_data'):
        st.divider()
        st.subheader("📄 Generated Lesson Plan")
        
        # Display the AI data in an expandable section
        with st.expander("View Lesson Plan Details", expanded=True):
            ai_data = st.session_state.ai_data
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Objectives:**")
                st.markdown(f"1. {ai_data.get('obj_1', 'N/A')}")
                st.markdown(f"2. {ai_data.get('obj_2', 'N/A')}")
                st.markdown(f"3. {ai_data.get('obj_3', 'N/A')}")
                
                st.markdown("**Topic:**")
                st.write(ai_data.get('topic', 'N/A'))
            
            with col2:
                st.markdown("**Integration:**")
                st.write(f"Within: {ai_data.get('integration_within', 'N/A')}")
                st.write(f"Across: {ai_data.get('integration_across', 'N/A')}")
        
        # Add a button to clear the generated plan
        if st.button("🗑️ Clear Current Plan", type="secondary"):
            st.session_state.generated = False
            st.session_state.ai_data = None
            st.rerun()

# --- 9. RUN THE APPLICATION ---
if __name__ == "__main__":
    main()
