import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from groq import Groq
import streamlit as st

load_dotenv()

@st.cache_resource
def get_clients():
    return genai.Client(), Groq(api_key=os.getenv("GROQ_API_KEY"))

gemini_client, groq_client = get_clients()

SYSTEM_PROMPT = """
Extract PayPal invoice details from the user request.

Return only JSON:
{
  "action": "create_invoice" or "unknown",
  "client_name": string or null,
  "amount": number or null,
  "currency": string or null,
  "description": string or null,
  "due_date": "YYYY-MM-DD" or null,
  "missing_fields": string[],
  "confirmation_message": string
}

If client_name, amount, or description is missing, use action "unknown" and ask for missing details.
Use today's date for relative dates. Today: {today}.
Never claim an invoice was created or sent.
"""

def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()

def use_groq(message: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT.replace("{today}", today)

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
    )

    return clean_json(response.choices[0].message.content)

def use_gemini(message: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT.replace("{today}", today)

    response = gemini_client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            {"role": "user", "parts": [{"text": prompt + "\n\nUser request: " + message}]}
        ],
    )

    return clean_json(response.text)

def interpret_request(message: str) -> str:
    try:
        return use_groq(message)
    except Exception as groq_error:
        try:
            return use_gemini(message)
        except Exception as gemini_error:
            return json.dumps({
                "action": "unknown",
                "client_name": None,
                "amount": None,
                "currency": None,
                "description": None,
                "due_date": None,
                "missing_fields": [],
                "confirmation_message": f"AI service unavailable. Groq error: {groq_error}; Gemini error: {gemini_error}"
            })