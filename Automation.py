import os
import requests
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Gemini API key is not set in environment variables.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

def process_uploaded_file(file):
    """
    Reads the content of the uploaded file based on its type.
    Supports PDF, DOCX, and TXT files.
    """
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            text = " ".join(page.extract_text() for page in reader.pages)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(file)
            text = " ".join(paragraph.text for paragraph in doc.paragraphs)
        elif file.type == "text/plain":
            text = file.read().decode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file.type}")
        return text
    except Exception as e:
        return f"Error processing file: {str(e)}"

def summarize_text(content):
    """
    Summarizes the given text using the Gemini model.
    """
    try:
        prompt = (
        f"Summarize the entire text in one line by maintaining all the necessary information given.\n"
        f"Include this line : If given product is about **Particular product given in text** then include this as context."
        f"You can take example of this summary :If given product is about Poultry Products like Chicken then include this as context: Malpractices across the poultry industry, from breeding and feeding to processing and marketing, involving unethical practices like substandard feed, hormone/antibiotic use, overcrowding, chemical contamination, mislabeling, and improper waste disposal, compromise product quality, endanger consumer health through antibiotic resistance, food poisoning, and chronic illnesses, and harm the environment, necessitating stronger regulations, education, traceability, sustainable practices, and rigorous testing. Improper Storage in Poultry products like ChickenImproper storage of poultry meat and eggs, including inadequate humidity/ventilation, cross-contamination, temperature abuse (freezer burn, improper refrigeration), chemical preservatives (formalin), dirty/cracked shells, moisture loss, and temperature fluctuations, leads to loss of nutritional quality, microbial growth (Salmonella, E. coli, Listeria, Campylobacter), spoilage, increased food waste, and human health impacts like chemical toxicity, foodborne illnesses (salmonellosis, listeriosis, campylobacteriosis), antibiotic resistance, and allergic reactions, necessitating consumer awareness, proper refrigeration, regular monitoring, and hygienic packaging.\n\n "
        f"Now summarize this : {content}"
    )
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        summary = response.text.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def append_to_text_file(file_name, summary):
    """
    Appends the summary to the Prompt.txt file and returns the file path.
    """
    prompt_file_path = "Prompt.txt"

    try:
        with open(prompt_file_path, "a", encoding="utf-8") as f:
            f.write(f"\n{summary}\n")
        return prompt_file_path
    except Exception as e:
        return f"Error appending to file: {str(e)}"
