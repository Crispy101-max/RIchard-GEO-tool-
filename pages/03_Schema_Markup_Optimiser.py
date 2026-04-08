import streamlit as st

if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please initialise a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

import os
import json
import re
from typing import Any, Dict, List

import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Schema Markup Optimiser",
    page_icon="🔖",
    layout="wide"
)


# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key() -> str:
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass

    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()

if not API_KEY:
    st.error(
        "No Gemini API key found. Add it in Streamlit secrets as API_Key."
    )
    st.stop()

client = genai.Client(api_key=API_KEY)


# ============================================================
# HELPERS
# ============================================================
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_json_from_model(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start:end + 1]
        return json.loads(snippet)

    raise ValueError("Could not parse valid JSON from model response.")


@st.cache_data(show_spinner=False)
def extract_page_for_schema(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""
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
        script_text = script.get_text(strip=True)
        if script_text:
            existing_jsonld.append(script_text)

    # Remove junk before text extraction
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))
    page_text = page_text[:25000]

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings[:20],
        "page_text": page_text,
        "existing_jsonld": existing_jsonld[:10],
    }


def call_gemini_schema(user_text: str, system_instruction: str, model_name: str = "gemini-2.5-pro") -> Dict[str, Any]:
    response = client.models.generate_content(
        model=model_name,
        config={"system_instruction": system_instruction},
        contents=[{"role": "user", "parts": [{"text": user_text}]}]
    )
    return {
        "text": response.text
    }


# ============================================================
# UI
# ============================================================
st.title("🔖 Schema Markup Optimiser")
st.write(
    "Generate and improve structured data for a page. "
    "This tool reads the visible page content, reviews any existing JSON-LD, "
    "and produces an improved schema draft plus a list of missing data and on-page improvements."
)

input_mode = st.radio(
    "Choose input type",
    ["URL", "Paste content manually"],
    horizontal=True
)

model_name = st.selectbox(
    "Choose model",
    ["gemini-2.5-pro", "gemini-2.5-flash"],
    index=0
)

source_data = None

if input_mode == "URL":
    url = st.text_input("Paste page URL", placeholder="https://example.com/product-page")
    run = st.button("Run Schema Optimiser", type="primary")

    if run:
        if not url.strip().startswith("http"):
            st.error("Please enter a valid URL starting with http or https.")
            st.stop()

        try:
            with st.spinner("Reading webpage..."):
                source_data = extract_page_for_schema(url)
        except Exception as e:
            st.error(f"Error reading webpage: {str(e)}")
            st.stop()

else:
    pasted_title = st.text_input("Page title (optional)")
    pasted_meta = st.text_input("Meta description (optional)")
    pasted_headings = st.text_area("Headings (one per line)", height=120)
    pasted_content = st.text_area("Paste the visible page content", height=250)
    pasted_existing_schema = st.text_area(
        "Paste existing JSON-LD schema if available (optional)",
        height=200
    )

    run = st.button("Run Schema Optimiser", type="primary")

    if run:
        if not pasted_content.strip():
            st.error("Please paste the page content.")
            st.stop()

        source_data = {
            "url": "",
            "title": pasted_title.strip(),
            "meta_description": pasted_meta.strip(),
            "headings": [h.strip() for h in pasted_headings.splitlines() if h.strip()],
            "page_text": clean_whitespace(pasted_content)[:25000],
            "existing_jsonld": [pasted_existing_schema.strip()] if pasted_existing_schema.strip() else [],
        }


# ============================================================
# MAIN RUN
# ============================================================
if source_data:
    SYSTEM_PROMPT = """
You are a structured data and schema markup strategist.

Your task:
1. Read the page content and any existing JSON-LD.
2. Identify the most appropriate schema type(s) for the page.
3. Improve or generate schema markup as JSON-LD.
4. NEVER invent facts not visible in the page content or existing schema.
5. If important information is missing, use placeholder strings in this exact format:
   [DATA NEEDED: short description]

Return VALID JSON ONLY in exactly this structure:
{
  "recommended_schema_types": ["..."],
  "current_schema_issues": ["..."],
  "on_page_improvements": ["..."],
  "missing_data": ["..."],
  "schema_jsonld": {},
  "implementation_notes": ["..."]
}

Rules:
- Only use facts visible in the source content or the existing JSON-LD.
- If multiple schema blocks are needed, "schema_jsonld" may be a list.
- Prefer JSON-LD using Schema.org vocabulary.
- Do not output explanations outside JSON.
"""

    USER_PROMPT = f"""
PAGE URL:
{source_data["url"]}

PAGE TITLE:
{source_data["title"]}

META DESCRIPTION:
{source_data["meta_description"]}

HEADINGS:
{json.dumps(source_data["headings"], ensure_ascii=False)}

VISIBLE PAGE CONTENT:
{source_data["page_text"]}

EXISTING JSON-LD ON PAGE:
{json.dumps(source_data["existing_jsonld"], ensure_ascii=False)}

Please:
- Identify the best schema type(s) for this page.
- Explain what is wrong or missing in the current schema situation.
- Suggest on-page content changes needed to support better markup.
- Output improved schema JSON-LD.
"""

    try:
        with st.spinner("Generating schema optimisation..."):
            result = call_gemini_schema(USER_PROMPT, SYSTEM_PROMPT, model_name=model_name)
            parsed = parse_json_from_model(result["text"])

        recommended_types = parsed.get("recommended_schema_types", [])
        current_issues = parsed.get("current_schema_issues", [])
        on_page_improvements = parsed.get("on_page_improvements", [])
        missing_data = parsed.get("missing_data", [])
        schema_jsonld = parsed.get("schema_jsonld", {})
        implementation_notes = parsed.get("implementation_notes", [])

        st.success("Schema analysis complete.")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Summary",
            "🧩 Optimised JSON-LD",
            "🛠 On-Page Improvements",
            "📋 Missing Data"
        ])

        with tab1:
            st.subheader("Recommended Schema Types")
            if recommended_types:
                for item in recommended_types:
                    st.write(f"- {item}")
            else:
                st.write("No schema types returned.")

            st.subheader("Current Schema Issues")
            if current_issues:
                for item in current_issues:
                    st.write(f"- {item}")
            else:
                st.write("No major issues returned.")

            st.subheader("Implementation Notes")
            if implementation_notes:
                for item in implementation_notes:
                    st.write(f"- {item}")
            else:
                st.write("No additional notes returned.")

        with tab2:
            st.subheader("Optimised JSON-LD")
            schema_pretty = json.dumps(schema_jsonld, indent=2, ensure_ascii=False)
            st.code(schema_pretty, language="json")

            st.download_button(
                label="⬇️ Download JSON-LD",
                data=schema_pretty,
                file_name="optimised_schema.json",
                mime="application/json",
                use_container_width=True
            )

        with tab3:
            st.subheader("On-Page Improvements Needed")
            if on_page_improvements:
                for item in on_page_improvements:
                    st.write(f"- {item}")
            else:
                st.write("No on-page improvements returned.")

        with tab4:
            st.subheader("Missing Data")
            if missing_data:
                for item in missing_data:
                    st.write(f"- {item}")
            else:
                st.write("No missing data returned.")

        with st.expander("See source content used by the tool"):
            st.write("**Title:**", source_data["title"])
            st.write("**Meta description:**", source_data["meta_description"])
            st.write("**Headings:**", source_data["headings"])
            st.text_area("Visible text extracted", source_data["page_text"], height=250)
            st.text_area(
                "Existing JSON-LD found",
                "\n\n".join(source_data["existing_jsonld"]) if source_data["existing_jsonld"] else "",
                height=200
            )

    except Exception as e:
        st.error(f"Error: {str(e)}")
