import bcrypt
import streamlit as st
st.set_page_config(page_title="Chatbot-Report Generator", layout="wide")
from streamlit_cookies_manager import EncryptedCookieManager
import os
from dotenv import load_dotenv
from fpdf import FPDF
import tempfile
import fitz 
from docx import Document 
import google.generativeai as genai
import csv
import requests
from bs4 import BeautifulSoup

load_dotenv()


cookies = EncryptedCookieManager(
    prefix="my_app",
    password=os.getenv("COOKIES_PASSWORD", "your_secret_password"),
)

if not cookies.ready():
    st.stop()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Gemini API key is not set in environment variables.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

USER_CSV_PATH = "users_data.csv"
QUESTIONS_CSV_PATH = "generated_questions.csv"

def save_generated_questions_to_csv(inputs, questions):
    """Save inputs and generated questions to a CSV file."""
    with open(QUESTIONS_CSV_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow([
                "Company Name", "Product Brand", "Product Description", "Production Location",
                "Geographical Area", "Production Volume", "Annual Revenue",
                "Additional Constraints", "Extracted Text", "Generated Questions"
            ])
        questions_text = "\n".join(questions)
        writer.writerow([
            inputs["Company Name"], inputs["Product Brand"], inputs["Product Description"],
            inputs["Production Location"], inputs["Geographical Area"], inputs["Production Volume"],
            inputs["Annual Revenue"], inputs["Additional Constraints"], inputs["Extracted Text"],
            questions_text
        ])

def scrape_website(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            heading = soup.find('h1').get_text(strip=True) if soup.find('h1') else "No heading found"
            article = " ".join([p.get_text(strip=True) for p in soup.find_all('p')])
            return heading, article
        else:
            st.error(f"Failed to fetch the URL. Status code: {response.status_code}")
            return None, None
    except Exception as e:
        st.error(f"An error occurred while scraping: {e}")
        return None, None

def load_users():
    """Load users from CSV file."""
    if os.path.exists(USER_CSV_PATH):
        with open(USER_CSV_PATH, mode="r") as file:
            reader = csv.DictReader(file)
            return {row["Username"]: row["PasswordHash"] for row in reader}
    return {}


def save_user(username, password_hash):
    """Save a new user to the CSV file."""
    with open(USER_CSV_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([username, password_hash])

def register_user(username, password):
    users = load_users()
    if username in users:
        st.warning("Username already exists.")
        return False

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    save_user(username, hashed_password.decode('utf-8'))
    st.success(f"User {username} registered successfully.")
    return True

def login_user(username, password):
    users = load_users()
    if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username].encode('utf-8')):
        st.session_state.logged_in = True
        st.session_state.username = username

        cookies["logged_in"] = "true"
        cookies["username"] = username
        cookies.save()

        return True
    else:
        st.error("Invalid username or password")
        return False

# Check if the user is logged in based on session state or cookies
if "logged_in" not in st.session_state:
    st.session_state.logged_in = cookies.get("logged_in") == "true"
    st.session_state.username = cookies.get("username", "")

if not st.session_state.logged_in:
    # User is not logged in, show login/register UI
    col_left, _, col_right = st.columns([1, 6, 1]) 
    with col_left:
        st.image("Altibbe logo dark.png", width=130)
    with col_right:
        st.image("Hedamo.jpg", width=200)

    st.markdown(
        """
        <h1 style='font-size:24px; color:black;'>Login and Register</h1>
        """, 
        unsafe_allow_html=True
    )

    auth_mode = st.radio("Choose Authentication Mode", ["Login(If registered)", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if auth_mode == "Register":
        if st.button("Register"):
            if username and password:
                register_user(username, password)
            else:
                st.warning("Please provide both username and password.")
    elif auth_mode == "Login(If registered)":
       if st.button("Login"):
         if username and password:
            if login_user(username, password): 
                st.success("Logged in successfully!")

                admin_username = "admin" 
                admin_password = "admin123"

                if username == admin_username and password == admin_password:
                    st.session_state['allow_admin_download'] = True
                else:
                    st.session_state['allow_admin_download'] = False

                st.rerun() 
else:
    if st.button("Logout"):
        cookies["logged_in"] = ""
        cookies["username"] = ""
        cookies.save()
        st.session_state.logged_in = False
        st.rerun()
    

    col_left, _, col_right = st.columns([1, 6, 1]) 

    with col_left:
        st.image("Altibbe logo dark.png", width=150)

    with col_right:
        st.image("Hedamo.jpg", width=200)

    st.markdown(
    """
    <a href="https://huggingface.co/spaces/abhi280622/Bhai-AI" target="_blank">
        <button style="padding:8px 15px; font-size:16px;">Go to Report Generator Chatbot</button>
    </a>
    """,
    unsafe_allow_html=True
    )

    st.markdown(
        """
        <h1 style='font-size:24px; color:black;'>Questionnaire Generator</h1>
        """,
        unsafe_allow_html=True,
    )

    st.write("Generate questions based on input data, including PDFs, text files, or Word documents.")

    st.markdown(
    """
    <h1 style='font-size:20px; color:black;'>Upload Files</h1>
    """, 
    unsafe_allow_html=True
)


    uploaded_files = st.file_uploader(
        "Upload files (PDF, text, or Word documents):",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
    )

    extracted_text = ""
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split(".")[-1].lower()
            try:
                if file_extension == "pdf":
                    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_file:
                        for page_num in range(pdf_file.page_count):
                            page = pdf_file[page_num]
                            extracted_text += page.get_text("text") + "\n"
                elif file_extension == "txt":
                    extracted_text += uploaded_file.read().decode("utf-8") + "\n"
                elif file_extension == "docx":
                    doc = Document(uploaded_file)
                    for para in doc.paragraphs:
                        extracted_text += para.text + "\n"
            except Exception as e:
                st.error(f"Error processing file '{uploaded_file.name}': {str(e)}")

    st.markdown(
    """
    <h1 style='font-size:20px; color:black;'>Additional Information</h1>
    """, 
    unsafe_allow_html=True
)
    specific_constraints = st.text_area(
        "Enter specific constraints or additional information for the questionnaire generation (optional):",
        height=150,
    )

    st.markdown(
    """
    <h1 style='font-size:20px; color:black;'>Product Details</h1>
    """, 
    unsafe_allow_html=True
)
    website_url = st.text_input("Website URL (Optional)")

    if website_url:
       heading, article = scrape_website(website_url)
       st.write(heading, article)

    col1, col2 = st.columns(2)
    production_volume=""
    annual_revenue=""
    with col1:
        company_name = st.text_input("Enter the name of the company:")
        product_brand = st.text_input("Enter the product brand:")
        product_description = st.text_input("Enter the product description:")
    with col2:
        production_location = st.text_input("Enter the production location:")
        geographical_area = st.text_input("Enter the geographical market:")
        production_volume = st.text_input("Enter the production volume:")
        annual_revenue = st.text_input("Enter the annual revenue:")

    st.markdown(
    """
    <h1 style='font-size:20px; color:black;'>Questionaire Generator Settings</h1>
    """, 
    unsafe_allow_html=True
)
    num_questions = st.number_input(
        "Enter the number of questions to generate:",
        min_value=1,
        max_value=100,
        value=30,
    )
    
    def generate_pdf(questions):
        pdf = FPDF()
        pdf.add_page()

        pdf.add_font('Roboto', '', 'Roboto-Regular.ttf', uni=True)
        pdf.add_font('Roboto-Bold', 'B', 'Roboto-Bold.ttf', uni=True)
        pdf.set_font('Roboto', size=12) 

        pdf.cell(200, 10, txt="Generated Questions", ln=True, align='C')
        pdf.ln(10)

        for i, question in enumerate(questions, 1):
           pdf.multi_cell(0, 10, f"{i}. {question}", ln=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_output_path = tmp_file.name
            pdf.output(pdf_output_path)

        return pdf_output_path

    if st.button("Generate Questions"):
        if not company_name or not product_brand or not product_description or not production_location or not geographical_area:
            st.warning("Please fill out all required fields in the Product Details section.")
        else:
            try:
                
                prompt = (
                    f"Generate a comprehensive questionnaire tailored for the product brand '{product_brand}', manufactured by '{company_name}', "
                    f"with a detailed description as '{product_description}', produced in '{production_location}', targeting the '{geographical_area}' geographical area. "
                    f"The production volume is '{production_volume}' and the annual revenue is '{annual_revenue}'. "
                    f"The questionnaire should focus on key areas relevant to health, quality, safety, sustainability, and brand positioning, "
                    f"specifically addressing the unique health benefits and consumer perceptions surrounding the product.\n\n"
                    f"Context from input files:\n{extracted_text} + {heading}+ {article}\n\n"
                    f"**Specific Constraints or Information:**\n{specific_constraints}\n\n"
                    f"**Instructions:**\n"
                    f"- Generate {2*num_questions // 3} short-answer questions, {num_questions // 6} multiple-choice questions (with 4 options each), "
                    f"and {num_questions//6} binary (Yes/No) questions. Generate the exact given number of questions.\n"
                    f"- Ensure questions are focused on product quality, compliance, good practices, brand positioning, and sustainability.\n\n"
                    f"**Key Objectives:**\n"
                    f"1. Investigate product-specific attributes such as health benefits, safety, and unique health propositions.\n"
                    f"2. Assess good practices, compliance with regulations, certifications, and ethical practices in business.\n"
                    f"3. Understand the current and planned market presence, brand perception, and pricing strategy.\n"
                    f"4. Inquire about production challenges, competitor analysis, and growth-oriented goals.\n"
                    f"5. Gather detailed insights into sustainable practices, including resource efficiency and waste management.\n"
                    f"6. Capture information regarding the company’s future commitments to health and sustainability improvements.\n\n"
                    f"7. Generate Questions in form such that my client has to answer about his product."
                    f"8. Don't Use symbols of currency. Rather use Name of Currency in response.",
                    f"9.Don't use some special symbols(like smart apostrophe) that connot be encoded using codec."
                    f"10. Use good Introduction and conclusion."
                    f"11. Question should be of top Quality."
                    f"12. Include scientific,geographic,different stages of production process with more emphasis  while generating questions."
                    f"13. Questions should be detailed and interesting to answer."
                    f"14. Do not Break questions on basis of any section like product , health, sustainability etc.."
                    f"15. Generate questions on different processes of making the product.Ex: Different stages of crop production,processing in industries etc.",
                    f"16. Also add the topic along with the generated questions( examples like: Health Attribute, production type, sustainability, marketing etc.)",
                    f"17. Questions should be in minimum 30 words and very descriptive and explained."
                )

                def generate_docx(questions, inputs):
                   """
                   Generates a DOCX file with questions and inputs and saves it to disk.
                   """
                   doc = Document()
                   doc.add_heading("Generated Questionnaire Report", level=1)
    
                   doc.add_heading("Inputs:", level=2)
                   for key, value in inputs.items():
                      doc.add_paragraph(f"{key}: {value}")
    
    
                   doc.add_heading("Generated Questions:", level=2)
                   for question in questions:
                      doc.add_paragraph(f"- {question}")
    
            
                   doc_path = "questionnaire_report.docx"
                   doc.save(doc_path)
                   return doc_path

# Main logic
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                questions = response.text.strip().split("\n")

                st.subheader("Generated Questions:")
                for q in questions:
                    st.write(f"- {q}")

                inputs = {
    "Company Name": company_name,
    "Product Brand": product_brand,
    "Product Description": product_description,
    "Production Location": production_location,
    "Geographical Area": geographical_area,
    "Production Volume": production_volume,
    "Annual Revenue": annual_revenue,
    "Additional Constraints": specific_constraints,
    "Extracted Text": extracted_text,
}

                save_generated_questions_to_csv(inputs, questions)

                pdf_path = generate_pdf(questions)
                docx_path = generate_docx(questions, inputs)
              
                with open(pdf_path, "rb") as pdf_file:
                     st.download_button(
                     "Download Full Report as PDF",
                     pdf_file,
                     file_name="questionnaire_report.pdf",
                    )
                with open(docx_path, "rb") as docx_file:
                     st.download_button(
                   "Download Full Report as DOCX",
                   docx_file,
                   file_name="questionnaire_report.docx",
        )

                if st.session_state.get('allow_admin_download'):
                   st.subheader("Admin Downloads")
                   st.download_button("Download CSV of Generated Questions", data=open("generated_questions.csv", "rb"), file_name="generated_questions.csv", mime="text/csv")
                   st.download_button("Download CSV of Registered Users", data=open("users_data.csv", "rb"), file_name="users_data.csv", mime="text/csv")
              
            except Exception as e:
                st.error(f"Error generating questions: {e}")
