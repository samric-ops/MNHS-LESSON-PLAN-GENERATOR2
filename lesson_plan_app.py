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

# --- 2. INITIALIZE SESSION STATE ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'ai_data' not in st.session_state:
    st.session_state.ai_data = None
if 'generated' not in st.session_state:
    st.session_state.generated = False

# --- 3. API KEY SETTINGS IN SIDEBAR ---
def add_api_settings():
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚙️ API Settings")
        
        # Instructions with link
        st.markdown("""
        **Get FREE API Key:**
        1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Click **"Get API Key"** → **"Create API Key"**
        3. Copy your key (starts with AIza)
        4. Paste below and click Save
        """)
        
        # API Key Input
        api_input = st.text_input(
            "Enter Google Gemini API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Your key will be saved only in this browser session"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key", use_container_width=True):
                if api_input and api_input.startswith("AIza"):
                    st.session_state.api_key = api_input.strip()
                    st.success("✅ API Key saved!")
                    st.rerun()
                else:
                    st.error("❌ Invalid key format")
        
        with col2:
            if st.button("🗑️ Clear", use_container_width=True, type="secondary"):
                st.session_state.api_key = None
                st.rerun()
        
        # Show current status
        if st.session_state.api_key:
            st.info(f"✅ Key: `{st.session_state.api_key[:10]}...`")
        else:
            st.warning("⚠️ No API key configured")
        
        st.markdown("---")

# --- 4. ORIGINAL HEADER FUNCTION (WITH FIX) ---
def add_custom_header():
    """Add custom header with maroon background (NO LOGOS)"""
    
    # Determine API status
    has_api_key = st.session_state.api_key is not None
    status_class = "api-active" if has_api_key else "api-inactive"
    status_text = "🔑 API: ACTIVE" if has_api_key else "⚠️ API: NOT CONFIGURED"
    
    st.markdown(f"""
    <style>
    .header-container {{
        text-align: center;
        padding: 20px;
        margin-bottom: 25px;
        background-color: #800000;
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
        color: #FFD700;
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
        color: #FFD700;
        margin-top: 8px;
        font-style: italic;
    }}
    
    /* App title styling */
    .app-title {{
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        color: #800000;
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
        
        <div class="api-status {status_class}">
            {status_text}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="app-title">📚 AI-Powered Lesson Plan Generator</p>', unsafe_allow_html=True)

# --- 5. ORIGINAL CLEAN JSON FUNCTION ---
def clean_json_string(json_string):
    """Clean the JSON string by removing invalid characters and fixing common issues"""
    if not json_string:
        return json_string
    
    # Remove markdown code blocks
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'```\s*', '', json_string)
    
    # Remove bullet points and other invalid characters
    json_string = json_string.replace('•', '-')
    json_string = json_string.replace('\u2022', '-')
    json_string = json_string.replace('\u25cf', '-')
    
    # Fix truncated strings (add closing quotes)
    json_string = re.sub(r':\s*$', '": ""', json_string)
    
    # Fix unclosed quotes in the middle of JSON
    lines = json_string.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        quote_count = line.count('"')
        
        if quote_count % 2 == 1 and ':' in line:
            last_colon_pos = line.rfind(':')
            if last_colon_pos > 0:
                after_colon = line[last_colon_pos + 1:].strip()
                if after_colon.startswith('"') and not after_colon.endswith('"'):
                    line = line + '"'
                elif not after_colon.startswith('"') and after_colon:
                    value_start = last_colon_pos + 1
                    while value_start < len(line) and line[value_start] in ' \t':
                        value_start += 1
                    if value_start < len(line):
                        line = line[:value_start] + '"' + line[value_start:] + '"'
        
        cleaned_lines.append(line)
    
    json_string = '\n'.join(cleaned_lines)
    
    # Remove any control characters
    json_string = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_string)
    
    # Fix common JSON issues
    json_string = re.sub(r',\s*}', '}', json_string)
    json_string = re.sub(r',\s*]', ']', json_string)
    
    return json_string

# --- 6. ORIGINAL IMAGE FETCHER ---
def fetch_ai_image(keywords):
    if not keywords: 
        keywords = "school_classroom"
    clean_prompt = re.sub(r'[\n\r\t]', ' ', str(keywords))
    clean_prompt = re.sub(r'[^a-zA-Z0-9 ]', '', clean_prompt).strip()
    
    encoded_prompt = urllib.parse.quote(clean_prompt)
    seed = random.randint(1, 9999)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=600&height=350&nologo=true&seed={seed}"
    url = url.strip()
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception:
        return None
    return None

# --- 7. ORIGINAL DOCX HELPERS ---
def set_cell_background(cell, color_hex):
    """Sets the background color of a table cell."""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def format_text(paragraph, text):
    """Parses text for ^ (superscript) and _ (subscript)."""
    if not text:
        return

    pattern = r"([^\^_]*)(([\^_])([0-9a-zA-Z\-]+))(.*)"
    current_text = str(text)
    
    if "^" not in current_text and "_" not in current_text:
        paragraph.add_run(current_text)
        return

    while True:
        match = re.match(pattern, current_text)
        if match:
            pre_text = match.group(1)
            marker = match.group(3)
            script_text = match.group(4)
            rest = match.group(5)
            
            if pre_text:
                paragraph.add_run(pre_text)
            
            run = paragraph.add_run(script_text)
            if marker == '^':
                run.font.superscript = True
            elif marker == '_':
                run.font.subscript = True
                
            current_text = rest
            if not current_text:
                break
        else:
            paragraph.add_run(current_text)
            break

def add_row(table, label, content, bold_label=True):
    """Adds a row and applies formatting to the content."""
    row_cells = table.add_row().cells
    
    # Label Column (Left)
    p_lbl = row_cells[0].paragraphs[0]
    run_lbl = p_lbl.add_run(label)
    if bold_label:
        run_lbl.bold = True
    
    # Content Column (Right)
    text_content = ""
    
    if isinstance(content, list):
        text_content = "\n".join([str(item) for item in content])
    else:
        text_content = str(content) if content else ""
    
    format_text(row_cells[1].paragraphs[0], text_content)

def add_section_header(table, text):
    """Adds a full-width section header with Blue background."""
    row = table.add_row()
    row.cells[0].merge(row.cells[1])
    cell = row.cells[0]
    cell.text = text
    cell.paragraphs[0].runs[0].bold = True
    set_cell_background(cell, "BDD7EE")

def parse_multiple_choice_question(q_text):
    """Parse a multiple choice question in format: question|A. choice1|B. choice2|C. choice3|D. choice4"""
    if not q_text:
        return "No question provided", []
    
    parts = q_text.split('|')
    
    if len(parts) < 5:
        return q_text, []
    
    question = parts[0].strip()
    choices = []
    
    for i in range(1, min(5, len(parts))):
        choice = parts[i].strip()
        if not re.match(r'^[A-D]\.', choice):
            choice_prefix = ['A.', 'B.', 'C.', 'D.'][i-1]
            choice = f"{choice_prefix} {choice}"
        choices.append(choice)
    
    while len(choices) < 4:
        choices.append(f"{['A.', 'B.', 'C.', 'D.'][len(choices)]} Choice placeholder")
    
    return question, choices

def add_assessment_row(table, label, eval_sec):
    """Special function to add assessment row with multiple choice questions."""
    row_cells = table.add_row().cells
    
    # Label Column (Left)
    p_lbl = row_cells[0].paragraphs[0]
    run_lbl = p_lbl.add_run(label)
    run_lbl.bold = True
    
    # Content Column (Right)
    content_cell = row_cells[1]
    
    # Clear cell
    for paragraph in content_cell.paragraphs:
        p = paragraph._element
        p.getparent().remove(p)
    
    # Create new content
    p_header = content_cell.add_paragraph()
    header_run = p_header.add_run("ASSESSMENT (5-item Multiple Choice Quiz)")
    header_run.bold = True
    
    p_dir = content_cell.add_paragraph()
    p_dir.add_run("DIRECTIONS: Read each question carefully. Choose the letter of the correct answer from options A, B, C, and D.")
    
    content_cell.add_paragraph()
    
    # Questions with multiple choice format
    for i in range(1, 6):
        question_key = f'assess_q{i}'
        raw_question = eval_sec.get(question_key, f'Question {i}')
        
        question_text, choices = parse_multiple_choice_question(raw_question)
        
        p_question = content_cell.add_paragraph()
        
        num_run = p_question.add_run(f"{i}. ")
        num_run.bold = True
        
        if question_text:
            format_text(p_question, question_text)
        
        if choices:
            for choice in choices:
                p_choice = content_cell.add_paragraph()
                p_choice.paragraph_format.left_indent = Inches(0.3)
                
                choice_match = re.match(r'^([A-D]\.)\s*(.*)', choice)
                if choice_match:
                    letter_part = choice_match.group(1)
                    text_part = choice_match.group(2)
                    
                    letter_run = p_choice.add_run(f"{letter_part} ")
                    letter_run.bold = True
                    
                    if text_part:
                        format_text(p_choice, text_part)
                else:
                    format_text(p_choice, choice)
        else:
            for letter in ['A.', 'B.', 'C.', 'D.']:
                p_choice = content_cell.add_paragraph()
                p_choice.paragraph_format.left_indent = Inches(0.3)
                letter_run = p_choice.add_run(f"{letter} ")
                letter_run.bold = True
                p_choice.add_run(f"Choice {letter[0]}")
        
        if i < 5:
            content_cell.add_paragraph()

# --- 8. ORIGINAL DOCX CREATOR ---
def create_docx(inputs, ai_data, teacher_name, principal_name, uploaded_image):
    doc = Document()
    
    # --- SETUP A4 PAGE SIZE & MARGINS ---
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

    # --- HEADER FOR DOCUMENT ---
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    dept_run = header_para.add_run("DEPARTMENT OF EDUCATION REGION XI\n")
    dept_run.bold = True
    dept_run.font.size = Pt(12)
    
    div_run = header_para.add_run("DIVISION OF DAVAO DEL SUR\n")
    div_run.bold = True
    div_run.font.size = Pt(11)
    
    school_run = header_para.add_run("MANUAL NATIONAL HIGH SCHOOL\n\n")
    school_run.bold = True
    school_run.font.size = Pt(14)
    
    title = doc.add_paragraph("Daily Lesson Log (DLL) / Daily Lesson Plan (DLP)")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    title.runs[0].font.size = Pt(14)

    # --- TOP INFO TABLE ---
    table_top = doc.add_table(rows=1, cols=4)
    table_top.style = 'Table Grid'
    table_top.autofit = False
    
    table_top.columns[0].width = Inches(2.5)
    table_top.columns[1].width = Inches(1.15)
    table_top.columns[2].width = Inches(1.15)
    table_top.columns[3].width = Inches(2.5)

    def fill_cell(idx, label, value):
        cell = table_top.rows[0].cells[idx]
        p = cell.paragraphs[0]
        p.add_run(label).bold = True
        p.add_run("\n")
        format_text(p, value)

    fill_cell(0, "Subject Area:", inputs['subject'])
    fill_cell(1, "Grade Level:", inputs['grade'])
    fill_cell(2, "Quarter:", inputs['quarter'])
    fill_cell(3, "Date:", date.today().strftime('%B %d, %Y'))

    # --- MAIN CONTENT TABLE ---
    table_main = doc.add_table(rows=0, cols=2)
    table_main.style = 'Table Grid'
    table_main.autofit = False
    
    table_main.columns[0].width = Inches(2.0)
    table_main.columns[1].width = Inches(5.3)

    # Process Data
    objs = f"1. {ai_data.get('obj_1','')}\n2. {ai_data.get('obj_2','')}\n3. {ai_data.get('obj_3','')}"
    r = ai_data.get('resources', {})
    proc = ai_data.get('procedure', {})
    eval_sec = ai_data.get('evaluation', {})

    # SECTION I
    add_section_header(table_main, "I. CURRICULUM CONTENT, STANDARD AND LESSON COMPETENCIES")
    add_row(table_main, "A. Content Standard", inputs['content_std'])
    add_row(table_main, "B. Performance Standard", inputs['perf_std'])
    
    row_comp = table_main.add_row().cells
    row_comp[0].paragraphs[0].add_run("C. Learning Competencies").bold = True
    p_comp = row_comp[1].paragraphs[0]
    p_comp.add_run("Competency: ").bold = True
    format_text(p_comp, inputs['competency'])
    p_comp.add_run("\n\nObjectives:\n").bold = True
    p_comp.add_run(objs)

    add_row(table_main, "D. Content", ai_data.get('topic', ''))
    add_row(table_main, "E. Integration", f"Within: {ai_data.get('integration_within','')}\nAcross: {ai_data.get('integration_across','')}")

    # SECTION II
    add_section_header(table_main, "II. LEARNING RESOURCES")
    add_row(table_main, "Teacher Guide", r.get('guide', ''))
    add_row(table_main, "Learner's Materials(LMs)", r.get('materials', ''))
    add_row(table_main, "Textbooks", r.get('textbook', ''))
    add_row(table_main, "Learning Resource (LR) Portal", r.get('portal', ''))
    add_row(table_main, "Other Learning Resources", r.get('other', ''))

    # SECTION III
    add_section_header(table_main, "III. TEACHING AND LEARNING PROCEDURE")
    add_row(table_main, "A. Activating Prior Knowledge", proc.get('review', ''))
    
    # --- IMAGE ROW ---
    row_img = table_main.add_row().cells
    row_img[0].paragraphs[0].add_run("B. Establishing Lesson Purpose").bold = True
    
    cell_img = row_img[1]
    format_text(cell_img.paragraphs[0], proc.get('purpose_situation', ''))
    cell_img.paragraphs[0].add_run("\n")
    
    img_data = None
    if uploaded_image:
        img_data = uploaded_image
    else:
        raw_prompt = proc.get('visual_prompt', 'school')
        img_data = fetch_ai_image(raw_prompt)
    
    if img_data:
        try:
            p_i = cell_img.add_paragraph()
            p_i.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_i = p_i.add_run()
            run_i.add_picture(img_data, width=Inches(3.5))
        except:
            cell_img.add_paragraph("[Image Error]")
    else:
        cell_img.add_paragraph("[No Image Available]")
        
    cell_img.add_paragraph(f"\nVocabulary:\n{proc.get('vocabulary','')}")

    # --- REVISED: C. Developing Understanding Section ---
    developing_content = f"Activity: {proc.get('activity_main','')}\n\n"
    developing_content += f"EXPLICITATION: {proc.get('explicitation','')}\n\n"
    developing_content += f"Group 1: {proc.get('group_1','')}\n"
    developing_content += f"Group 2: {proc.get('group_2','')}\n"
    developing_content += f"Group 3: {proc.get('group_3','')}"
    
    add_row(table_main, "C. Developing Understanding", developing_content)
    add_row(table_main, "D. Making Generalization", proc.get('generalization', ''))

    # SECTION IV - REVISED ASSESSMENT SECTION
    add_section_header(table_main, "IV. EVALUATING LEARNING")
    add_assessment_row(table_main, "A. Assessment", eval_sec)
    add_row(table_main, "B. Assignment", eval_sec.get('assignment', ''))
    
    # Save document
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    
    return doc_io

# --- 9. REVISED AI GENERATOR FUNCTION ---
def generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency, 
                           obj_cognitive=None, obj_psychomotor=None, obj_affective=None,
                           lesson_topic=None):
    try:
        # Check if API key exists
        if not st.session_state.api_key:
            st.error("❌ No API key configured. Please enter your Google Gemini API key in the sidebar settings.")
            return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
        # Configure with user's API key
        genai.configure(api_key=st.session_state.api_key)
        
        # Try multiple model options
        model_options = ['gemini-1.5-flash', 'gemini-1.5-pro']
        model = None
        
        for model_name in model_options:
            try:
                model = genai.GenerativeModel(model_name)
                test_response = model.generate_content("Hello")
                if test_response:
                    st.sidebar.success(f"✓ Using model: {model_name}")
                    break
            except Exception as e:
                continue
        
        if not model:
            model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Check if user provided objectives
        user_provided_objectives = obj_cognitive and obj_psychomotor and obj_affective
        
        # Check if user provided topic (optional)
        user_provided_topic = lesson_topic and lesson_topic.strip()
        
        if user_provided_objectives or user_provided_topic:
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
            ai_data = json.loads(cleaned_text)
            
            # If user provided topic but AI didn't use it, override
            if user_provided_topic and 'topic' in ai_data:
                ai_data['topic'] = lesson_topic
                
            return ai_data
        except json.JSONDecodeError as je:
            st.error(f"JSON Parsing Error: {je}")
            return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)
        
    except Exception as e:
        st.error(f"AI Generation Error: {str(e)}")
        return create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic)

# --- 10. SAMPLE DATA FUNCTION ---
def create_sample_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Create sample data for demonstration"""
    topic = lesson_topic if lesson_topic else f"Introduction to {subject}"
    
    return {
        "obj_1": f"Understand {subject} concepts",
        "obj_2": f"Apply {subject} skills",
        "obj_3": f"Appreciate the value of {subject}",
        "topic": topic,
        "integration_within": f"Related {subject} topics",
        "integration_across": "Mathematics, Science",
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
            "vocabulary": "Term1: Definition1\nTerm2: Definition2\nTerm3: Definition3\nTerm4: Definition4\nTerm5: Definition5",
            "activity_main": "Group activity to explore the topic",
            "explicitation": f"Detailed explanation of {subject} with examples. Example 1: Basic application. Example 2: Advanced application.",
            "group_1": "Research task",
            "group_2": "Problem-solving task",
            "group_3": "Presentation task",
            "generalization": "What did you learn? How can you apply this?"
        },
        "evaluation": {
            "assess_q1": f"What is the main concept of {subject}?|A. Concept A|B. Concept B|C. Concept C|D. Concept D",
            "assess_q2": f"How would you apply {subject} in real life?|A. Application A|B. Application B|C. Application C|D. Application D",
            "assess_q3": f"Explain the difference between key terms in {subject}.|A. Difference A|B. Difference B|C. Difference C|D. Difference D",
            "assess_q4": f"Solve a simple problem using {subject} concepts.|A. Solution A|B. Solution B|C. Solution C|D. Solution D",
            "assess_q5": f"What are the limitations of {subject} approaches?|A. Limitation A|B. Limitation B|C. Limitation C|D. Limitation D",
            "assignment": "Research more about the topic",
            "remarks": "Lesson delivered successfully",
            "reflection": "Students showed good understanding"
        }
    }

# --- 11. MAIN APPLICATION ---
def main():
    # Add API settings to sidebar
    add_api_settings()
    
    # Add custom header
    add_custom_header()
    
    # Main form for lesson plan generation
    with st.form("lesson_form"):
        st.subheader("📝 Lesson Plan Details")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            subject = st.selectbox("Subject Area", 
                                 ["Mathematics", "Science", "English", "Filipino", "Araling Panlipunan", 
                                  "MAPEH", "ESP", "TLE", "Research", "Statistics"])
        with col2:
            grade = st.selectbox("Grade Level", ["7", "8", "9", "10", "11", "12"])
        with col3:
            quarter = st.selectbox("Quarter", ["1", "2", "3", "4"])
        
        content_std = st.text_area("Content Standard", 
                                 placeholder="The learner demonstrates understanding of...")
        perf_std = st.text_area("Performance Standard", 
                              placeholder="The learner is able to...")
        competency = st.text_area("Learning Competency", 
                                placeholder="E.g., Differentiates between...")
        
        # Optional custom objectives
        with st.expander("➕ Custom Objectives (Optional)"):
            col_obj1, col_obj2, col_obj3 = st.columns(3)
            with col_obj1:
                obj_cognitive = st.text_input("Cognitive", 
                                            placeholder="E.g., Analyze the concept of...")
            with col_obj2:
                obj_psychomotor = st.text_input("Psychomotor", 
                                              placeholder="E.g., Create a model showing...")
            with col_obj3:
                obj_affective = st.text_input("Affective", 
                                            placeholder="E.g., Appreciate the importance of...")
        
        lesson_topic = st.text_input("Lesson Topic (Optional)", 
                                   placeholder="E.g., Photosynthesis, Quadratic Equations...")
        
        # Teacher and Principal names
        col_teacher, col_principal = st.columns(2)
        with col_teacher:
            teacher_name = st.text_input("Teacher's Name", value="")
        with col_principal:
            principal_name = st.text_input("Principal's Name", value="")
        
        # Image upload
        uploaded_image = st.file_uploader("Upload Lesson Image (Optional)", 
                                        type=['png', 'jpg', 'jpeg'])
        
        # Generate button
        if st.session_state.api_key:
            btn_text = "🤖 Generate AI Lesson Plan"
            btn_help = "Uses Google Gemini AI with your API key"
        else:
            btn_text = "👁️ View Sample Lesson Plan"
            btn_help = "Shows sample plan without API key"
        
        generate_btn = st.form_submit_button(
            btn_text,
            help=btn_help,
            type="primary",
            use_container_width=True
        )
    
    # Handle form submission
    if generate_btn:
        with st.spinner("🔄 Generating your lesson plan..."):
            # Prepare inputs
            inputs = {
                'subject': subject,
                'grade': grade,
                'quarter': quarter,
                'content_std': content_std,
                'perf_std': perf_std,
                'competency': competency
            }
            
            # Generate lesson content
            ai_data = generate_lesson_content(
                subject, grade, quarter, content_std, perf_std, competency,
                obj_cognitive, obj_psychomotor, obj_affective, lesson_topic
            )
            
            if ai_data:
                st.session_state.ai_data = ai_data
                st.session_state.generated = True
                st.session_state.inputs = inputs
                st.session_state.teacher_name = teacher_name
                st.session_state.principal_name = principal_name
                st.session_state.uploaded_image = uploaded_image
                
                if st.session_state.api_key:
                    st.success("✅ AI Lesson Plan Generated Successfully!")
                else:
                    st.success("✅ Sample Lesson Plan Generated!")
    
    # Display generated lesson plan
    if st.session_state.get('generated') and st.session_state.get('ai_data'):
        st.divider()
        st.subheader("📄 Generated Lesson Plan")
        
        # Display preview
        with st.expander("📋 Preview Lesson Plan", expanded=True):
            ai_data = st.session_state.ai_data
            
            # Display in columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📚 Objectives:**")
                st.write(f"1. {ai_data.get('obj_1', 'N/A')}")
                st.write(f"2. {ai_data.get('obj_2', 'N/A')}")
                st.write(f"3. {ai_data.get('obj_3', 'N/A')}")
                
                st.markdown("**🎯 Topic:**")
                st.write(ai_data.get('topic', 'N/A'))
                
                st.markdown("**🔗 Integration:**")
                st.write(f"**Within:** {ai_data.get('integration_within', 'N/A')}")
                st.write(f"**Across:** {ai_data.get('integration_across', 'N/A')}")
            
            with col2:
                st.markdown("**📖 Resources:**")
                resources = ai_data.get('resources', {})
                st.write(f"• Teacher Guide: {resources.get('guide', 'N/A')}")
                st.write(f"• Learner Materials: {resources.get('materials', 'N/A')}")
                st.write(f"• Textbook: {resources.get('textbook', 'N/A')}")
                st.write(f"• LR Portal: {resources.get('portal', 'N/A')}")
                st.write(f"• Other: {resources.get('other', 'N/A')}")
        
        # Download button for DOCX
        if st.session_state.get('inputs'):
            docx_file = create_docx(
                st.session_state.inputs,
                st.session_state.ai_data,
                st.session_state.teacher_name,
                st.session_state.principal_name,
                st.session_state.uploaded_image
            )
            
            st.download_button(
                label="📥 Download as DOCX",
                data=docx_file,
                file_name=f"Lesson_Plan_{subject}_Grade{grade}_Q{quarter}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        
        # Clear button
        if st.button("🗑️ Clear Current Plan", type="secondary", use_container_width=True):
            st.session_state.generated = False
            st.session_state.ai_data = None
            st.rerun()

# --- 12. RUN THE APPLICATION ---
if __name__ == "__main__":
    main()
