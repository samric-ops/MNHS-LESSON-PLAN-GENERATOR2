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

# --- 2. API KEY EMBEDDED IN CODE ---
# Replace this with your actual Google AI API key
EMBEDDED_API_KEY = "AIzaSyDadTf3EpAs-gm0VIg3A9yxVoNqjw7yvhA"  # REPLACE WITH YOUR ACTUAL KEY

# --- 3. SIMPLIFIED HEADER WITHOUT LOGOS ---
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
        font-weight = True
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

# --- 4. AI GENERATOR ---
def clean_json_string(json_string):
    """Clean the JSON string by removing invalid characters and fixing common issues"""
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

def generate_lesson_content(subject, grade, quarter, content_std, perf_std, competency, 
                           obj_cognitive=None, obj_psychomotor=None, obj_affective=None,
                           lesson_topic=None):
    try:
        # Use the embedded API key
        genai.configure(api_key=EMBEDDED_API_KEY)
        
        # Try multiple model options
        model_options = ['gemini-2.5-flash']
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

def create_fallback_data(subject, grade, quarter, content_std, perf_std, competency, lesson_topic=None):
    """Create fallback data in case AI generation fails"""
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

# --- 5. IMAGE FETCHER ---
def fetch_ai_image(keywords):
    if not keywords: keywords = "school_classroom"
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

# --- 6. DOCX HELPERS ---
def set_cell_background(cell, color_hex):
    """Sets the background color of a table cell."""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def format_text(paragraph, text):
    """
    Parses text for ^ (superscript) and _ (subscript).
    """
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
        # Join list items with newlines for vertical stacking
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
    
    # Split by pipe character
    parts = q_text.split('|')
    
    if len(parts) < 5:
        # If not in expected format, return as-is
        return q_text, []
    
    question = parts[0].strip()
    choices = []
    
    # Extract choices (should be 4 choices)
    for i in range(1, min(5, len(parts))):
        choice = parts[i].strip()
        # Ensure choice starts with letter and period
        if not re.match(r'^[A-D]\.', choice):
            # Add prefix if missing
            choice_prefix = ['A.', 'B.', 'C.', 'D.'][i-1]
            choice = f"{choice_prefix} {choice}"
        choices.append(choice)
    
    # Ensure we have exactly 4 choices
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
    
    # Content Column (Right) - Build from scratch
    content_cell = row_cells[1]
    
    # Clear cell by removing all existing paragraphs
    for paragraph in content_cell.paragraphs:
        p = paragraph._element
        p.getparent().remove(p)
    
    # Create new content
    # 1. Header
    p_header = content_cell.add_paragraph()
    header_run = p_header.add_run("ASSESSMENT (5-item Multiple Choice Quiz)")
    header_run.bold = True
    
    # 2. Directions
    p_dir = content_cell.add_paragraph()
    p_dir.add_run("DIRECTIONS: Read each question carefully. Choose the letter of the correct answer from options A, B, C, and D.")
    
    # 3. Empty line for spacing
    content_cell.add_paragraph()
    
    # 4. Questions with multiple choice format
    for i in range(1, 6):
        question_key = f'assess_q{i}'
        raw_question = eval_sec.get(question_key, f'Question {i}')
        
        # Parse multiple choice question
        question_text, choices = parse_multiple_choice_question(raw_question)
        
        # Create question paragraph
        p_question = content_cell.add_paragraph()
        
        # Add question number (bold)
        num_run = p_question.add_run(f"{i}. ")
        num_run.bold = True
        
        # Add question text with formatting
        if question_text:
            format_text(p_question, question_text)
        
        # Add choices (A, B, C, D)
        if choices:
            for choice in choices:
                p_choice = content_cell.add_paragraph()
                p_choice.paragraph_format.left_indent = Inches(0.3)
                
                # Make the choice letter bold (A., B., etc.)
                choice_match = re.match(r'^([A-D]\.)\s*(.*)', choice)
                if choice_match:
                    letter_part = choice_match.group(1)
                    text_part = choice_match.group(2)
                    
                    letter_run = p_choice.add_run(f"{letter_part} ")
                    letter_run.bold = True
                    
                    if text_part:
                        format_text(p_choice, text_part)
                else:
                    # Fallback if format doesn't match
                    format_text(p_choice, choice)
        else:
            # Fallback: create placeholder choices
            for letter in ['A.', 'B.', 'C.', 'D.']:
                p_choice = content_cell.add_paragraph()
                p_choice.paragraph_format.left_indent = Inches(0.3)
                letter_run = p_choice.add_run(f"{letter} ")
                letter_run.bold = True
                p_choice.add_run(f"Choice {letter[0]}")
        
        # Add spacing between questions (except after last question)
        if i < 5:
            content_cell.add_paragraph()

# --- 7. DOCX CREATOR ---
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
    # Add school header to document
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Department line
    dept_run = header_para.add_run("DEPARTMENT OF EDUCATION REGION XI\n")
    dept_run.bold = True
    dept_run.font.size = Pt(12)
    
    # Division line
    div_run = header_para.add_run("DIVISION OF DAVAO DEL SUR\n")
    div_run.bold = True
    div_run.font.size = Pt(11)
    
    # School line
    school_run = header_para.add_run("MANUAL NATIONAL HIGH SCHOOL\n\n")
    school_run.bold = True
    school_run.font.size = Pt(14)
    
    # Title - CHANGED TO: Daily Lesson Log (DLL) / Daily Lesson Plan (DLP)
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
    # Create the content for this section with the new format
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
    add_row(table_main, "C. Remarks", eval_sec.get('remarks', ''))
    add_row(table_main, "D. Reflection", eval_sec.get('reflection', ''))

    doc.add_paragraph()

    # --- SIGNATORIES TABLE ---
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.autofit = False
    
    sig_table.columns[0].width = Inches(4.0)
    sig_table.columns[1].width = Inches(4.0)
    
    row = sig_table.rows[0]
    
    # LEFT COLUMN: TEACHER SIGNATURE
    teacher_cell = row.cells[0]
    
    teacher_header_p = teacher_cell.add_paragraph()
    teacher_header_run = teacher_header_p.add_run("Prepared by:")
    teacher_header_run.bold = True
    
    teacher_cell.add_paragraph()
    
    teacher_name_p = teacher_cell.add_paragraph()
    teacher_name_run = teacher_name_p.add_run(teacher_name)
    teacher_name_run.bold = True
    
    teacher_position_p = teacher_cell.add_paragraph()
    teacher_position_p.add_run("Teacher III")
    
    # RIGHT COLUMN: PRINCIPAL SIGNATURE
    principal_cell = row.cells[1]
    
    principal_header_p = principal_cell.add_paragraph()
    principal_header_run = principal_header_p.add_run("Noted by:")
    principal_header_run.bold = True
    
    principal_cell.add_paragraph()
    
    principal_name_p = principal_cell.add_paragraph()
    principal_name_run = principal_name_p.add_run(principal_name)
    principal_name_run.bold = True
    
    principal_position_p = principal_cell.add_paragraph()
    principal_position_p.add_run("Principal III")

    # Save to BytesIO
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 8. STREAMLIT UI ---
def main():
    # Add custom header with maroon background (NO LOGOS)
    add_custom_header()
    
    # App Title - IN ONE LINE with custom styling
    st.markdown('<p class="app-title">Daily Lesson Plan (DLP) Generator</p>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("📋 User Information")
        
        # Set default names to the required values
        teacher_name = st.text_input("Teacher Name", value="RICHARD P. SAMORANOS")
        principal_name = st.text_input("Principal Name", value="ROSALITA A. ESTROPIA")
        
        st.markdown("---")
        st.info("Upload an image (optional) for the lesson")
        uploaded_image = st.file_uploader("Choose an image for lesson", type=['png', 'jpg', 'jpeg'], key="lesson")
        
        # Removed the API Key message from here
    
    # Form Inputs
    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.text_input("Subject Area", placeholder="e.g., Mathematics")
    
    with col2:
        # Grade Level Dropdown - Kinder to Grade 12
        grade_options = [
            "Kinder",
            "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6",
            "Grade 7", "Grade 8", "Grade 9", "Grade 10",
            "Grade 11", "Grade 12"
        ]
        grade = st.selectbox("Grade Level", grade_options, index=6)  # Default to Grade 7
    
    with col3:
        # Quarter Dropdown - Roman Numerals
        quarter_options = ["I", "II", "III", "IV"]
        quarter = st.selectbox("Quarter", quarter_options, index=2)  # Default to Quarter III
    
    content_std = st.text_area("Content Standard", placeholder="The learner demonstrates understanding of...")
    perf_std = st.text_area("Performance Standard", placeholder="The learner is able to...")
    competency = st.text_area("Learning Competency", placeholder="Competency code and description...")
    
    st.markdown("---")
    
    # --- OPTIONAL: LESSON CONTENT/TOPIC SECTION ---
    with st.expander("📚 Optional: Lesson Content / Topic", expanded=False):
        st.info("Enter the specific topic or content for this lesson. Leave blank if you want AI to generate it.")
        
        lesson_topic = st.text_area(
            "Lesson Content / Topic",
            placeholder="e.g., Introduction to Quadratic Equations: Solving ax^2 + bx + c = 0\nOr leave blank for AI to generate",
            height=120,
            help="Optional: The main content or topic that will be taught in this lesson. Include specific concepts, formulas, or key points."
        )
    
    st.markdown("---")
    
    # --- OPTIONAL: LESSON OBJECTIVES SECTION ---
    with st.expander("📝 Optional: Lesson Objectives", expanded=False):
        st.info("If you already have your lesson objectives, enter them below. Otherwise, leave blank and AI will generate them.")
        
        col_obj1, col_obj2, col_obj3 = st.columns(3)
        
        with col_obj1:
            obj_cognitive = st.text_area(
                "Cognitive Objective",
                placeholder="e.g., Identify the parts of a cell\n(Leave blank for AI)",
                height=100,
                help="What students should know or understand"
            )
        
        with col_obj2:
            obj_psychomotor = st.text_area(
                "Psychomotor Objective",
                placeholder="e.g., Draw and label the parts of a cell\n(Leave blank for AI)",
                height=100,
                help="What students should be able to do"
            )
        
        with col_obj3:
            obj_affective = st.text_area(
                "Affective Objective",
                placeholder="e.g., Appreciate the complexity of living organisms\n(Leave blank for AI)",
                height=100,
                help="Values, attitudes, or emotions to develop"
            )
    
    st.markdown("---")
    
    # Generate Button
    if st.button("🚀 Generate DLP", type="primary", use_container_width=True):
        if not all([subject, grade, quarter, content_std, perf_std, competency]):
            st.error("Please fill all required fields")
            return
        
        # Check if user provided content (all optional)
        user_provided_topic = lesson_topic and lesson_topic.strip()
        user_provided_objectives = obj_cognitive and obj_psychomotor and obj_affective
        
        # Show what user is providing
        provided_items = []
        if user_provided_topic:
            provided_items.append("topic")
        if user_provided_objectives:
            provided_items.append("objectives")
        
        if provided_items:
            st.info(f"✅ Using your provided: {', '.join(provided_items)}")
            st.info("🔧 AI will generate the remaining content")
        else:
            st.info("🔧 AI will generate all lesson content for you")
        
        with st.spinner("🤖 Generating lesson content..."):
            ai_data = generate_lesson_content(
                subject, grade, quarter, 
                content_std, perf_std, competency,
                obj_cognitive if obj_cognitive else None,
                obj_psychomotor if obj_psychomotor else None,
                obj_affective if obj_affective else None,
                lesson_topic if user_provided_topic else None
            )
            
        if ai_data:
            st.success("✅ AI content generated successfully!")
            
            # Show topic preview
            st.subheader("📚 Generated Lesson Content")
            col_topic, col_integration = st.columns(2)
            
            with col_topic:
                st.info("**Main Topic**")
                st.write(ai_data.get('topic', 'N/A'))
            
            with col_integration:
                st.info("**Integration**")
                st.write(f"Within Subject: {ai_data.get('integration_within', 'N/A')}")
                st.write(f"Across Subjects: {ai_data.get('integration_across', 'N/A')}")
            
            # Show objectives preview
            st.subheader("📋 Generated Objectives")
            col_obj_pre1, col_obj_pre2, col_obj_pre3 = st.columns(3)
            
            with col_obj_pre1:
                st.info("**Cognitive**")
                st.write(ai_data.get('obj_1', 'N/A'))
            
            with col_obj_pre2:
                st.info("**Psychomotor**")
                st.write(ai_data.get('obj_2', 'N/A'))
            
            with col_obj_pre3:
                st.info("**Affective**")
                st.write(ai_data.get('obj_3', 'N/A'))
            
            # Show assessment preview
            with st.expander("📝 Preview Assessment Questions"):
                for i in range(1, 6):
                    question_key = f'assess_q{i}'
                    raw_question = ai_data.get('evaluation', {}).get(question_key, '')
                    if raw_question:
                        question_text, choices = parse_multiple_choice_question(raw_question)
                        st.markdown(f"**Question {i}:** {question_text}")
                        if choices:
                            for choice in choices:
                                st.write(f"  {choice}")
                        st.markdown("---")
            
            # Full preview
            with st.expander("📄 Preview All Generated Content"):
                st.json(ai_data)
            
            # Create DOCX
            inputs = {
                'subject': subject,
                'grade': grade,
                'quarter': quarter,
                'content_std': content_std,
                'perf_std': perf_std,
                'competency': competency
            }
            
            with st.spinner("📄 Creating DOCX file..."):
                docx_buffer = create_docx(inputs, ai_data, teacher_name, principal_name, uploaded_image)
            
            # Download button
            st.download_button(
                label="📥 Download DLP (.docx)",
                data=docx_buffer,
                file_name=f"DLP_{subject}_{grade}_Q{quarter}_{date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
            
            # Display success message
            st.balloons()
            st.success(f"✅ DLP generated for {subject} - {grade} - Quarter {quarter}")
        else:
            st.error("Failed to generate AI content. Please try again.")

if __name__ == "__main__":
    main()

