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

DATABASE_URL = os.getenv("NEON_DB_URL")
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

def create_tables():
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        tables = ["food", "clothes", "cosmetics"]
        for table in tables:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        conn.commit()
        cursor.close()
        conn.close()

def insert_food(summary):
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO food (summary) VALUES (%s)", (summary,))
            conn.commit()
            st.success("Food summary saved successfully!")
        except Exception as e:
            st.error(f"Error inserting into food table: {e}")
        finally:
            cursor.close()
            conn.close()

def insert_clothes(summary):
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO clothes (summary) VALUES (%s)", (summary,))
            conn.commit()
            st.success("Clothes summary saved successfully!")
        except Exception as e:
            st.error(f"Error inserting into clothes table: {e}")
        finally:
            cursor.close()
            conn.close()

def insert_cosmetics(summary):
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO cosmetics (summary) VALUES (%s)", (summary,))
            conn.commit()
            st.success("Cosmetics summary saved successfully!")
        except Exception as e:
            st.error(f"Error inserting into cosmetics table: {e}")
        finally:
            cursor.close()
            conn.close()

def process_uploaded_file(file):
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
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
    
create_tables()
