import streamlit as st

if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please initialise a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

import os
import json
import re
import requests
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Content Optimiser",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ GEO Content Optimiser")
st.write(
    "Rewrite webpages so they are clearer, better structured, and easier for "
    "AI systems to understand, cite, and trust — then visualise the result."
)

# ============================================================
# API KEY
# ============================================================
def get_api_key():
    if "API_Key" in st.secrets:
        return st.secrets["API_Key"]
    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY")


API_KEY = get_api_key()
if not API_KEY:
    st.error("No Gemini API key found. Add it as `API_Key` in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-pro"

# ============================================================
# HELPERS
# ============================================================
def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def domain_to_brand(url):
    try:
        netloc = urlparse(url).netloc.replace("www.", "")
        return netloc.split(".")[0].replace("-", " ").title()
    except Exception:
        return "Brand"


@st.cache_data(show_spinner=False)
def extract_page(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else domain_to_brand(url)

    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc = meta["content"].strip()

    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]

    schema_blocks = [
        s.get_text(strip=True)
        for s in soup.find_all("script", type="application/ld+json")
        if s.get_text(strip=True)
    ]

    for el in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        el.decompose()

    text = clean(soup.get_text(separator=" ", strip=True))[:25000]

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings[:20],
        "text": text,
        "schema": schema_blocks[:10],
        "brand": domain_to_brand(url)
    }


def call_gemini(user_prompt, system_prompt, json_mode=False):
    config = {
        "temperature": 0,
        "top_p": 0.1,
        "top_k": 1,
        "max_output_tokens": 8192,
        "seed": 42,
        "system_instruction": system_prompt,
    }
    if json_mode:
        config["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(**config),
        contents=user_prompt,
    )
    return response

# ============================================================
# SESSION STATE
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================================
# UI
# ============================================================
prompt = st.chat_input("Enter URL (starting with http) or paste website content...")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    if prompt.strip().startswith("http"):
        with st.spinner("Reading website..."):
            page = extract_page(prompt)
            source_text = page["text"]
            title = page["title"]
            brand = page["brand"]
    else:
        source_text = clean(prompt)
        title = "Pasted Content"
        brand = "Brand"

    SYSTEM_PROMPT = """
You are a senior Generative Engine Optimisation (GEO) strategist.

Rewrite the content so it is:
- Clear and explicit
- Structurally easy for AI systems to interpret
- Answer-first and entity-aware

Rules:
- Do NOT invent facts
- Do NOT add fake statistics
- Use [DATA NEEDED: ...] placeholders where information is missing

Return JSON ONLY in exactly this structure:

{
  "rewritten_content": ""
}
"""

    USER_PROMPT = f"""
BRAND:
{brand}

PAGE TITLE:
{title}

SOURCE CONTENT:
{source_text}
"""

    with st.spinner("Optimising content for GEO..."):
        response = call_gemini(USER_PROMPT, SYSTEM_PROMPT, json_mode=True)
        rewritten = json.loads(response.text)["rewritten_content"]

    st.session_state.messages.append({
        "role": "assistant",
        "content": rewritten
    })

    st.rerun()
