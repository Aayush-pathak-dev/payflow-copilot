import os
import json
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai
from groq import Groq
import streamlit as st
from agents import Agent, Runner


load_dotenv()


@st.cache_resource
def get_clients():
    return genai.Client(), Groq(api_key=os.getenv("GROQ_API_KEY"))


gemini_client, groq_client = get_clients()


SYSTEM_PROMPT = """
You are PayFlow Copilot. Extract invoice details from the user's request.

Return ONLY valid JSON. Do not add explanations, markdown, or extra text.

Use this exact JSON structure:

{
  "action": "create_invoice",
  "client_name": "",
  "client_email": "",
  "amount": 0,
  "currency": "USD",
  "description": "",
  "due_date": ""
}

Rules:
- Extract the customer email address into client_email.
- If the user provides an email address, action must be "create_invoice".
- If no email address is provided, set client_email to null and action to "missing_info".
- Use ISO date format YYYY-MM-DD for due_date.
- If due date is not specified, calculate it as 7 days from today.
- Today's date is {today}.
- Currency must be a three-letter ISO currency code such as USD, INR, EUR, or GBP.
- If currency is not specified, use USD.
- Do not include markdown links, explanations, or text outside JSON.

Examples:

User: Create a $250 invoice for Rahul Sharma at rahul@example.com for 10 hours of web design, due in 7 days
Response:
{
  "action": "create_invoice",
  "client_name": "Rahul Sharma",
  "client_email": "rahul@example.com",
  "amount": 250,
  "currency": "USD",
  "description": "10 hours of web design",
  "due_date": "2026-11-15"
}

User: Create a $100 invoice for Alex
Response:
{
  "action": "missing_info",
  "client_name": "Alex",
  "client_email": null,
  "amount": 100,
  "currency": "USD",
  "description": "",
  "due_date": "2026-11-15"
}
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

    if not response.choices:
        raise ValueError("Groq returned no response choices.")

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Groq returned an empty response.")

    return clean_json(content)


def use_gemini(message: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT.replace("{today}", today)

    response = gemini_client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt + "\n\nUser request: " + message
                    }
                ],
            }
        ],
        config={
            "response_mime_type": "application/json",
        },
    )

    return clean_json(response.text)


def interpret_request(message: str) -> str:
    try:
        return use_groq(message)

    except Exception as groq_error:
        try:
            return use_gemini(message)

        except Exception as gemini_error:
            return json.dumps(
                {
                    "action": "unknown",
                    "client_name": None,
                    "client_email": None,
                    "amount": None,
                    "currency": None,
                    "description": None,
                    "due_date": None,
                    "missing_fields": [],
                    "confirmation_message": (
                        f"AI service unavailable. "
                        f"Groq error: {groq_error}; "
                        f"Gemini error: {gemini_error}"
                    ),
                }
            )