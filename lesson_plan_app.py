import streamlit as st
import google.generativeai as genai
import json
from datetime import date
import io
import requests
import urllib.parse
import random
import re
import hashlib

# --- NEW LIBRARY FOR WORD DOCS ---
from docx import Document
from docx.shared import Inches, Pt, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DLP Generator", layout="centered")

# --- 2. SIMPLIFIED HEADER WITHOUT LOGOS ---
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
    </style>
    
    <div class="header-container">
        <p class="dept-name">DEPARTMENT OF EDUCATION REGION XI</p>
        <p class="division-name">DIVISION OF DAVAO DEL SUR</p>
        <p class="school-name">MANUAL NATIONAL HIGH SCHOOL</p>
        <p class="header-subtext">Kiblawan North District</p>
    </div>
    """, unsafe_allow_html=True)

# --- 3. API KEY MANAGER WITH REMEMBER FEATURE ---
def save_api_key(api_key):
    if api_key:
        st.session_state.api_key = api_key
        st.session_state.saved_api_key = api_key
        return True
    return False

def load_saved_api_key():
    return st.session_state.get('saved_api_key', '')

def show_api_key_settings():
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 API Key Settings")
    
    if 'saved_api_key' not in st.session_state:
        st.session_state.saved_api_key = ""
    
    saved_key = load_saved_api_key()
    input_key = f"api_key_input_{hashlib.md5(saved_key.encode() if saved_key else ''.encode()).hexdigest()[:8]}"
    
    api_key = st.sidebar.text_input(
        "Enter your Google Gemini API Key:",
        type="password",
        placeholder="AIzaSy...",
        value=saved_key,
        key=input_key,
        help="Enter your free API key from Google AI Studio"
    )
    
    remember_me = st.sidebar.checkbox("Remember my API key", value=bool(saved_key))
    
    if st.sidebar.button("💾 Save API Key", use_container_width=True):
        if api_key:
            if save_api_key(api_key):
                st.sidebar.success("✅ API Key Saved!")
            else:
                st.sidebar.error("❌ Failed to save API key")
        else:
            st.sidebar.warning("⚠️ Please enter an API key")
            
    if saved_key:
        if st.sidebar.button("🗑️ Clear Saved Key", use_container_width=True):
            st.session_state.saved_api_key = ""
            st.session_state.api_key = ""
            st.sidebar.success("✅ API Key Cleared!")
            st.rerun()

    if st.sidebar.button("📋 How to Get Free API Key", use_container_width=True):
        st.session_state.show_instructions = True

    if st.session_state.get('api_key'):
        st.sidebar.success("✅ API Key Ready")
    else:
        st.sidebar.warning("⚠️ API Key Required")

    if api_key and remember_me and api_key != saved_key:
        save_api_key(api_key)
    
    return api_key

def show_api_key_instructions_page():
    st.title("FREE API Key Instructions")
    st.write("Instruction content here...") 
    if st.button("← BACK TO DLP GENERATOR", use_container_width=True):
        st.session_state.show_instructions = False
        st.rerun()

# --- 4. AI GENERATOR (UPDATED FOR LANGUAGE FLEXIBILITY) ---
def clean_json_string(json_string):
    if not json_string: return json_string
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'```\s*', '', json_string)
    json_string = json_string.replace('•', '-')
    return json_string

def generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency, 
                           obj_cognitive=None, obj_psychomotor=None, obj_affective=None,
                           lesson_topic=None):
    try:
        current_api_key = st.session_state.get('api_key') or st.session_state.get('saved_api_key')
        
        if not current_api_key:
            st.error("❌ Please enter your Google Gemini API Key in the sidebar")
            return None
        
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # --- LOGIC PARA SA WIKA (Language Logic) ---
        # Check kung ang subject ay nangangailangan ng Tagalog
        subj_lower = subject.lower()
        tagalog_subjects = ['filipino', 'araling panlipunan', 'edukasyon sa pagpapakatao', 'esp', 'ap', 'values education']
        
        is_tagalog_context = any(s in subj_lower for s in tagalog_subjects)
        
        if is_tagalog_context:
            language_instruction = """
            *** LANGUAGE SETTING: FILIPINO / TAGALOG ***
            The subject is detected as Filipino, Araling Panlipunan, or ESP.
            You MUST generate the CONTENT values (objectives, activities, procedures, questions) in TAGALOG/FILIPINO.
            You may use English terms if there is no direct translation (Taglish is okay if necessary).
            
            IMPORTANT: Keep the JSON KEYS (e.g., "obj_1", "procedure", "review") in ENGLISH. Only the VALUES should be in Filipino.
            """
        else:
            language_instruction = """
            *** LANGUAGE SETTING: ENGLISH ***
            Generate all content in English.
            """

        # Base Prompt
        prompt_parts = [
            f"""You are an expert teacher from Manual National High School.
            Create a JSON object for a Daily Lesson Plan (DLP).
            Subject: {subject}, Grade: {grade}, Quarter: {quarter}
            Content Standard: {content_std}
            Performance Standard: {perf_std}
            Learning Competency: {competency}
            
            {language_instruction}
            """]
            
        # Add user inputs if present
        if obj_cognitive and obj_psychomotor and obj_affective:
            prompt_parts.append(f"""
            USER-PROVIDED OBJECTIVES (Adapt language if needed):
            - Cognitive: {obj_cognitive}
            - Psychomotor: {obj_psychomotor}
            - Affective: {obj_affective}""")
            
        if lesson_topic:
            prompt_parts.append(f"""
            TOPIC: {lesson_topic}""")

        # Structural Instructions
        prompt_parts.append(f"""
            CRITICAL INSTRUCTIONS:
            1. Generate exactly 5 MULTIPLE CHOICE assessment questions.
            2. Format: "question|A. choice1|B. choice2|C. choice3|D. choice4"
            3. Return ONLY valid JSON.
            
            Structure:
            {{
                "obj_1": "Cognitive objective",
                "obj_2": "Psychomotor objective",
                "obj_3": "Affective objective",
                "topic": "The main topic",
                "integration_within": "Topic within same subject",
                "integration_across": "Topic across other subject",
                "resources": {{ "guide": "", "materials": "", "textbook": "", "portal": "", "other": "" }},
                "procedure": {{
                    "review": "Review activity",
                    "purpose_situation": "Motivation",
                    "visual_prompt": "3-word visual description for image generation (English)",
                    "vocabulary": "Terms and definitions",
                    "activity_main": "Main activity",
                    "explicitation": "Analysis and abstraction",
                    "group_1": "Task 1", "group_2": "Task 2", "group_3": "Task 3",
                    "generalization": "Abstraction/Generalization"
                }},
                "evaluation": {{
                    "assess_q1": "Q1...", "assess_q2": "Q2...", "assess_q3": "Q3...", "assess_q4": "Q4...", "assess_q5": "Q5...",
                    "assignment": "Assignment",
                    "remarks": "Remarks",
                    "reflection": "Reflection"
                }}
            }}
            """)
            
        prompt = "\n".join(prompt_parts)
        
        # Generate
        response = model.generate_content(prompt)
        text = clean_json_string(response.text)
        
        try:
            # Parse JSON
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group(0))
                # Override topic if user provided one
                if lesson_topic and 'topic' in ai_data:
                    ai_data['topic'] = lesson_topic
                return ai_data
            else:
                return json.loads(text)
        except Exception:
            # Fallback
            return create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)

    except Exception as e:
        st.error(f"Error: {e}")
        return create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)

def create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Simple fallback data if AI fails"""
    return {
        "obj_1": "N/A", "obj_2": "N/A", "obj_3": "N/A",
        "topic": lesson_topic if lesson_topic else subject,
        "integration_within": "", "integration_across": "",
        "resources": {"guide": "", "materials": "", "textbook": "", "portal": "", "other": ""},
        "procedure": {
            "review": "", "purpose_situation": "", "visual_prompt": "School", "vocabulary": "",
            "activity_main": "", "explicitation": "", "group_1": "", "group_2": "", "group_3": "", "generalization": ""
        },
        "evaluation": {
            "assess_q1": "Question|A. 1|B. 2|C. 3|D. 4", 
            "assignment": "", "remarks": "", "reflection": ""
        }
    }

# --- 5. IMAGE FETCHER ---
def fetch_ai_image(keywords):
    if not keywords: keywords = "school_classroom"
    clean_prompt = re.sub(r'[\n\r\t]', ' ', str(keywords))
    clean_prompt = re.sub(r'[^a-zA-Z0-9 ]', '', clean_prompt).strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)
    seed = random.randint(1, 9999)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=600&height=350&nologo=true&seed={seed}"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception:
        return None
    return None

# --- 6. DOCX HELPERS ---
def set_cell_background(cell, color_hex):
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def format_text(paragraph, text):
    paragraph.add_run(str(text)) # Simplified for stability

def add_row(table, label, content, bold_label=True):
    row_cells = table.add_row().cells
    p_lbl = row_cells[0].paragraphs[0]
    run = p_lbl.add_run(label)
    if bold_label: run.bold = True
    content_text = "\n".join([str(item) for item in content]) if isinstance(content, list) else str(content)
    format_text(row_cells[1].paragraphs[0], content_text)

def add_section_header(table, text):
    row = table.add_row()
    row.cells[0].merge(row.cells[1])
    cell = row.cells[0]
    cell.text = text
    cell.paragraphs[0].runs[0].bold = True
    set_cell_background(cell, "BDD7EE")

def parse_multiple_choice_question(q_text):
    if not q_text: return "No question", []
    parts = q_text.split('|')
    if len(parts) < 2: return q_text, []
    question = parts[0].strip()
    choices = [p.strip() for p in parts[1:] if p.strip()]
    return question, choices

def add_assessment_row(table, label, eval_sec):
    row_cells = table.add_row().cells
    row_cells[0].paragraphs[0].add_run(label).bold = True
    
    cell = row_cells[1]
    # Clear existing
    for p in cell.paragraphs: 
        p._element.getparent().remove(p._element)
    
    cell.add_paragraph().add_run("ASSESSMENT").bold = True
    
    for i in range(1, 6):
        q_key = f'assess_q{i}'
        raw = eval_sec.get(q_key, "")
        q_text, choices = parse_multiple_choice_question(raw)
        
        if q_text:
            p = cell.add_paragraph()
            p.add_run(f"{i}. ").bold = True
            p.add_run(q_text)
            for c in choices:
                cell.add_paragraph(c, style='List Bullet')
        cell.add_paragraph() # Spacer

# --- 7. DOCX CREATOR (FIXED & COMPLETED) ---
def create_docx(inputs, ai_data, teacher_name, principal_name, uploaded_image):
    doc = Document()
    
    # Page Setup
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    for margin in [section.top_margin, section.bottom_margin, section.left_margin, section.right_margin]:
        margin = Inches(0.5)

    # Header
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_para.add_run("DEPARTMENT OF EDUCATION REGION XI\n").bold = True
    header_para.add_run("DIVISION OF DAVAO DEL SUR\n").bold = True
    header_para.add_run("MANUAL NATIONAL HIGH SCHOOL\n\n").bold = True
    
    # Title
    title = doc.add_paragraph("DAILY LESSON PLAN")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(16)
    
    # Info Table
    table = doc.add_table(rows=0, cols=2)
    table.style = 'Table Grid'
    table.autofit = False
    table.columns[0].width = Inches(1.5)
    table.columns[1].width = Inches(6.0)
    
    # Fill Table
    add_section_header(table, "I. OBJECTIVES")
    add_row(table, "Content Standard:", inputs['content_std'])
    add_row(table, "Performance Standard:", inputs['perf_std'])
    add_row(table, "Learning Competency:", inputs['competency'])
    add_row(table, "Objectives:", [
        f"Cognitive: {ai_data.get('obj_1', '')}",
        f"Psychomotor: {ai_data.get('obj_2', '')}",
        f"Affective: {ai_data.get('obj_3', '')}"
    ])
    
    add_section_header(table, "II. CONTENT")
    add_row(table, "Topic:", ai_data.get('topic', ''))
    
    add_section_header(table, "III. LEARNING RESOURCES")
    res = ai_data.get('resources', {})
    add_row(table, "References:", [
        f"Guide: {res.get('guide', '')}",
        f"Materials: {res.get('materials', '')}",
        f"Textbook: {res.get('textbook', '')}"
    ])
    
    add_section_header(table, "IV. PROCEDURES")
    proc = ai_data.get('procedure', {})
    add_row(table, "A. Review:", proc.get('review', ''))
    add_row(table, "B. Purpose/Motivation:", proc.get('purpose_situation', ''))
    
    # Image insertion logic inside table
    if uploaded_image:
        row = table.add_row()
        cell = row.cells[1]
        p = cell.paragraphs[0]
        run = p.add_run()
        run.add_picture(uploaded_image, width=Inches(3.0))
    else:
        # Try fetch AI image
        img_prompt = proc.get('visual_prompt', 'school')
        img_bytes = fetch_ai_image(img_prompt)
        if img_bytes:
            row = table.add_row()
            cell = row.cells[1]
            p = cell.paragraphs[0]
            run = p.add_run()
            try:
                run.add_picture(img_bytes, width=Inches(3.0))
            except:
                pass

    add_row(table, "C. Activity:", proc.get('activity_main', ''))
    add_row(table, "D. Analysis:", proc.get('explicitation', ''))
    add_row(table, "E. Abstraction:", proc.get('generalization', ''))
    add_row(table, "F. Application:", [
        f"Group 1: {proc.get('group_1', '')}",
        f"Group 2: {proc.get('group_2', '')}",
        f"Group 3: {proc.get('group_3', '')}"
    ])
    
    add_section_header(table, "V. EVALUATION")
    add_assessment_row(table, "Assessment:", ai_data.get('evaluation', {}))
    add_row(table, "Assignment:", ai_data.get('evaluation', {}).get('assignment', ''))
    
    add_section_header(table, "VI. REMARKS & REFLECTION")
    add_row(table, "Remarks:", ai_data.get('evaluation', {}).get('remarks', ''))
    
    # Signatures
    sig_para = doc.add_paragraph("\n\nPrepared by:\n\n")
    sig_para.add_run(f"{teacher_name.upper()}\n").bold = True
    sig_para.add_run("Teacher")
    
    sig_para.add_run("\n\nChecked by:\n\n")
    sig_para.add_run(f"{principal_name.upper()}\n").bold = True
    sig_para.add_run("Principal / School Head")
    
    # Save to IO
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 8. MAIN UI ---
def main():
    if 'show_instructions' not in st.session_state:
        st.session_state.show_instructions = False

    if st.session_state.show_instructions:
        show_api_key_instructions_page()
        return

    add_custom_header()
    show_api_key_settings()
    
    st.markdown("<h1 class='app-title'>✨ Smart Lesson Plan Generator</h1>", unsafe_allow_html=True)
    
    with st.form("dlp_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject (e.g., Filipino, Science)", "Filipino 8")
            grade = st.text_input("Grade Level", "Grade 8")
            quarter = st.selectbox("Quarter", ["First", "Second", "Third", "Fourth"])
            teacher_name = st.text_input("Teacher's Name", "JUAN D. CRUZ")
        with col2:
            content_std = st.text_area("Content Standard", "Naipamamalas ang...")
            perf_std = st.text_area("Performance Standard", "Naisasagawa ang...")
            competency = st.text_area("Learning Competency", "Nahihinuha ang...")
            principal_name = st.text_input("Principal's Name", "MARIA A. SANTOS")
            
        st.markdown("### 🎯 Specific Objectives (Optional)")
        c1, c2, c3 = st.columns(3)
        obj_cog = c1.text_input("Cognitive")
        obj_psy = c2.text_input("Psychomotor")
        obj_aff = c3.text_input("Affective")
        topic = st.text_input("Specific Topic (Optional)")
        
        uploaded_file = st.file_uploader("Upload Image (Optional)", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("🚀 Generate Lesson Plan", type="primary")

    if submitted:
        if not st.session_state.get('api_key') and not st.session_state.get('saved_api_key'):
            st.error("⚠️ Please enter your API Key in the sidebar first!")
        else:
            with st.spinner("🤖 AI is thinking... (Checking subject language...)"):
                # Call generator
                ai_data = generate_lesson_content(
                    subject, grade, quarter, content_std, perf_std, competency,
                    obj_cog, obj_psy, obj_aff, topic
                )
                
                if ai_data:
                    st.success("✅ Content Generated!")
                    
                    # Preview
                    with st.expander("📄 View Generated Content (JSON Preview)"):
                        st.json(ai_data)
                    
                    # Create Doc
                    docx_file = create_docx(
                        {'content_std': content_std, 'perf_std': perf_std, 'competency': competency},
                        ai_data, teacher_name, principal_name, uploaded_file
                    )
                    
                    st.download_button(
                        label="💾 Download Word Document (.docx)",
                        data=docx_file,
                        file_name=f"DLP_{subject}_{date.today()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

if __name__ == "__main__":
    main()
