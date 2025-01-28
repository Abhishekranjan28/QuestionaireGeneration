import os
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv
import streamlit as st
import psycopg2
import pandas as pd

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Gemini API key is not set in environment variables.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

DATABASE_URL = os.getenv("RENDER_DB_URL")
if not DATABASE_URL:
    st.error("PostgreSQL connection string is not set in environment variables.")
    st.stop()

def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return None

def create_table():
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

def save_summary_to_db(summary):
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO summaries (summary) 
                VALUES (%s)
            """, (summary,))
            conn.commit()
            st.success("Summary saved to the database successfully!")
        except Exception as e:
            st.error(f"Error saving summary to the database: {e}")
        finally:
            cursor.close()
            conn.close()

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
            f"Summarize the entire text in one line by maintaining all the necessary information given in approx 150 words.\n"
            f"Include this line: **If given product is about **Product given in text**, then include this as context :**\n\n"
            f"Now summarize this: {content}"
        )
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        summary = response.text.strip()
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"
    
create_table()
