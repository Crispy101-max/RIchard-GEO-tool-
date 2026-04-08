import os
import json
import re
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-pro"
GENERATION_SEED = 42


def get_api_key():
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass

    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


def get_client():
    api_key = get_api_key()
    if not api_key:
        st.error("No Gemini API key found. Add it in Streamlit secrets as `API_Key`.")
        st.stop()
    return genai.Client(api_key=api_key)


def ensure_geo_context():
    if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
        st.warning("Run the GEO workflow from the Home page first.")
        st.stop()
    return st.session_state.geo_context


def clean_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def domain_to_brand(url):
    try:
        netloc = urlparse(url).netloc.replace("www.", "")
        brand = netloc.split(".")[0]
        return brand.replace("-", " ").replace("_", " ").title()
    except Exception:
        return "Brand"


@st.cache_data(show_spinner=False)
def fetch_page_snapshot(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else domain_to_brand(url)

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        txt = clean_whitespace(h.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    existing_jsonld = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = script.get_text(strip=True)
        if txt:
            existing_jsonld.append(txt)

    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))
    page_text = page_text[:30000]

    return {
        "url": url,
        "title": title,
        "brand_name": domain_to_brand(url),
        "meta_description": meta_description,
        "headings": headings[:25],
        "page_text": page_text,
        "existing_jsonld": existing_jsonld[:10],
    }


def parse_model_json(text):
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return valid JSON.")

    snippet = cleaned[start:end + 1]
    return json.loads(snippet)


def call_gemini_json(client, system_prompt, user_prompt, max_output_tokens=8192):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            candidate_count=1,
            max_output_tokens=max_output_tokens,
            seed=GENERATION_SEED,
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return parse_model_json(response.text)


def call_gemini_text(client, system_prompt, user_prompt, max_output_tokens=8192):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            candidate_count=1,
            max_output_tokens=max_output_tokens,
            seed=GENERATION_SEED,
            system_instruction=system_prompt,
        ),
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:html|markdown|text)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    return text.strip()


def replace_data_needed_boxes(text):
    pattern = r"\[DATA NEEDED:(.*?)\]"

    def repl(match):
        content = match.group(1).strip()
        return (
            '<div class="data-needed">'
            "<strong>DATA NEEDED</strong><br>"
            f"{content}"
            "</div>"
        )

    return re.sub(pattern, repl, text)


def simple_markdown_to_html(text):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = replace_data_needed_boxes(safe)

    lines = safe.split("\n")
    html_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            html_parts.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            html_parts.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("- "):
            html_parts.append(f"<li>{stripped[2:]}</li>")
        else:
            html_parts.append(f"<p>{stripped}</p>")

    final_parts = []
    in_list = False

    for part in html_parts:
        if part.startswith("<li>"):
            if not in_list:
                final_parts.append("<ul>")
                in_list = True
            final_parts.append(part)
        else:
            if in_list:
                final_parts.append("</ul>")
                in_list = False
            final_parts.append(part)

    if in_list:
        final_parts.append("</ul>")

    return "\n".join(final_parts)


def build_mock_html(title, badge, content_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
body {{
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    line-height: 1.6;
}}
.container {{
    width: min(1100px, calc(100% - 32px));
    margin: 0 auto;
    padding: 32px 0 56px;
}}
.card {{
    background: #1e293b;
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 30px 60px rgba(0,0,0,.35);
    border: 1px solid rgba(255,255,255,.08);
}}
.badge {{
    display: inline-block;
    margin-bottom: 16px;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(99,102,241,.18);
    color: #c7d2fe;
    font-size: .85rem;
}}
h1, h2, h3 {{
    color: white;
    margin-top: 24px;
}}
p {{
    color: #cbd5e1;
}}
ul {{
    padding-left: 22px;
}}
li {{
    margin-bottom: 8px;
}}
.data-needed {{
    border: 2px dashed #ef4444;
    background: rgba(239,68,68,.08);
    color: #fecaca;
    padding: 16px;
    border-radius: 14px;
    margin: 16px 0;
}}
footer {{
    margin-top: 24px;
    text-align: center;
    color: #94a3b8;
    font-size: .9rem;
}}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <div class="badge">{badge}</div>
    {content_html}
  </div>
  <footer>Mock webpage preview generated from GEO workflow context.</footer>
</div>
</body>
</html>
"""
