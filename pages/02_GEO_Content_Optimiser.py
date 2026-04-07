import os
import json
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
import streamlit as st
import streamlit.components.v1 as components
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

# ============================================================
# CONSTANTS
# ============================================================
HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")

DEFAULT_PALETTE = {
    "background": "#0f172a",
    "surface": "#1e293b",
    "accent": "#6366f1",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
}

MODEL_NAME = "gemini-2.5-pro"
GENERATION_SEED = 42

# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key() -> str:
    if "API_Key" in st.secrets:
        return st.secrets["API_Key"]
    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()
if not API_KEY:
    st.error(
        "No Gemini API key found.\n\n"
        "Add it in Streamlit secrets as `API_Key`."
    )
    st.stop()

client = genai.Client(api_key=API_KEY)

# ============================================================
# HELPERS
# ============================================================
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def domain_to_brand(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.replace("www.", "")
        brand = netloc.split(".")[0]
        return brand.replace("-", " ").replace("_", " ").title()
    except Exception:
        return "Brand"


def extract_hex_colours(css_text: str, inline_styles: List[str]) -> List[str]:
    combined = (css_text or "") + "\n" + "\n".join(inline_styles or [])
    colours = HEX_PATTERN.findall(combined)
    seen, cleaned = set(), []

    for c in colours:
        c = c.lower()
        if len(c) == 4:
            c = "#" + "".join(ch * 2 for ch in c[1:])
        if c not in seen:
            seen.add(c)
            cleaned.append(c)
    return cleaned[:10]


def infer_palette(colours: List[str]) -> Dict[str, str]:
    palette = DEFAULT_PALETTE.copy()
    keys = ["accent", "background", "surface", "text", "muted"]
    for i, key in enumerate(keys):
        if i < len(colours):
            palette[key] = colours[i]
    return palette


def extract_website_data(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else domain_to_brand(url)

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    css_text = "\n".join(s.get_text(" ", strip=True) for s in soup.find_all("style"))

    inline_styles = [
        tag.get("style", "")
        for tag in soup.find_all(style=True)
        if "color" in tag.get("style", "").lower()
    ]

    colours = extract_hex_colours(css_text, inline_styles)

    headings = [
        clean_whitespace(h.get_text(" ", strip=True))
        for h in soup.find_all(["h1", "h2", "h3"])
        if clean_whitespace(h.get_text(" ", strip=True))
    ]

    existing_jsonld = [
        s.get_text(strip=True)
        for s in soup.find_all("script", type="application/ld+json")
        if s.get_text(strip=True)
    ]

    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))[:25000]

    return {
        "url": url,
        "title": title,
        "brand_name": domain_to_brand(url),
        "meta_description": meta_description,
        "headings": headings[:20],
        "page_text": page_text,
        "raw_css_excerpt": css_text[:4000],
        "inline_styles_excerpt": inline_styles[:20],
        "existing_jsonld": existing_jsonld[:10],
        "colours": colours,
        "palette": infer_palette(colours),
    }


def parse_json_from_model(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|html)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned[cleaned.find("{"): cleaned.rfind("}") + 1])


def html_looks_valid(html: str) -> bool:
    return html.strip().lower().startswith("<!doctype html")


def call_gemini(user_text: str, system_instruction: str, json_mode: bool = False):
    cfg = {
        "temperature": 0,
        "top_p": 0.1,
        "top_k": 1,
        "candidate_count": 1,
        "max_output_tokens": 8192,
        "seed": GENERATION_SEED,
        "system_instruction": system_instruction,
    }
    if json_mode:
        cfg["response_mime_type"] = "application/json"

    return client.models.generate_content(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(**cfg),
        contents=[{"role": "user", "parts": [{"text": user_text}]}],
    )

# ============================================================
# SESSION STATE
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "scores" not in st.session_state:
    st.session_state.scores = {
        "AI_Readability": "0",
        "Fact_Density": "0",
        "Authority": "0",
    }

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("📊 GEO Scoreboard")
    st.metric("AI Readability", f"{st.session_state.scores['AI_Readability']}/100")
    st.metric("Fact Density", f"{st.session_state.scores['Fact_Density']}%")
    st.metric("Entity Authority", f"{st.session_state.scores['Authority']}/100")
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# ============================================================
# MAIN UI
# ============================================================
st.title("✍️ GEO Content Optimiser")
st.write(
    "Rewrite webpages so they are clearer, more structured, and easier for "
    "AI systems to understand, cite, and trust — then visualise the result."
)

# ============================================================
# CHAT LOOP (UNCHANGED BEHAVIOUR)
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Enter URL (starting with http) or paste website content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
``
