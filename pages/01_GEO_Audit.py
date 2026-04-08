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
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Audit",
    page_icon="📋",
    layout="wide"
)

st.title("📋 GEO Audit")
st.write(
    "Assess how well a webpage is positioned for **Generative Engine Optimisation (GEO)**. "
    "This is a strategic audit — not a rewrite."
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


@st.cache_data(show_spinner=False)
def fetch_page(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

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

    text = clean(soup.get_text(separator=" ", strip=True))[:30000]

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings[:25],
        "text": text,
        "schema": schema_blocks[:10],
    }


def call_gemini(user_prompt, system_prompt):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            max_output_tokens=8192,
            seed=42,
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)

# ============================================================
# INPUT
# ============================================================
url = st.text_input("Website page URL", placeholder="https://example.com/page")

external_visibility = st.text_area(
    "External brand visibility signals (optional)",
    placeholder="Paste metrics from Amplitude, GA4, Profound, etc.",
    height=120
)

run = st.button("Run GEO Audit", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a senior Generative Engine Optimisation (GEO) auditor.

Assess how well the page is positioned for AI understanding and citation.

Consider:
- Content structure & clarity
- Entity definition
- Knowledge graph readiness
- Schema posture
- Citation readiness
- Real-world brand visibility (if provided)

Do NOT rewrite content.
Do NOT invent facts.

Return JSON ONLY in this structure:

{
  "overall_summary": "",
  "strengths": [],
  "weaknesses": [],
  "opportunities": [],
  "visibility_context": {
    "summary": "",
    "impact_on_priorities": ""
  },
  "schema_snapshot": {
    "current_state": "",
    "recommended_focus": []
  },
  "entity_readiness": {
    "assessment": "",
    "gaps": []
  },
  "citation_readiness": {
    "assessment": "",
    "gaps": []
  },
  "priority_actions": []
}
"""

# ============================================================
# RUN AUDIT
# ============================================================
if run:
    if not url.startswith("http"):
        st.error("Please enter a valid URL.")
        st.stop()

    try:
        with st.spinner("Fetching page..."):
            page = fetch_page(url)

        USER_PROMPT = f"""
URL:
{url}

TITLE:
{page["title"]}

META DESCRIPTION:
{page["meta_description"]}

HEADINGS:
{json.dumps(page["headings"], ensure_ascii=False)}

PAGE CONTENT:
{page["text"]}

EXISTING SCHEMA:
{json.dumps(page["schema"], ensure_ascii=False)}

EXTERNAL VISIBILITY:
{external_visibility if external_visibility else "None provided"}
"""

        with st.spinner("Running GEO audit..."):
            audit = call_gemini(USER_PROMPT, SYSTEM_PROMPT)

        st.success("GEO audit complete")

        st.subheader("Overall Summary")
        st.write(audit["overall_summary"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("✅ Strengths")
            for i in audit["strengths"]:
                st.write(f"- {i}")

        with col2:
            st.subheader("❌ Weaknesses")
            for i in audit["weaknesses"]:
                st.write(f"- {i}")

        with col3:
            st.subheader("🚀 Opportunities")
            for i in audit["opportunities"]:
                st.write(f"- {i}")

        st.divider()

        st.subheader("📈 Visibility Context")
        st.write(audit["visibility_context"]["summary"])
        st.write(audit["visibility_context"]["impact_on_priorities"])

        st.subheader("🧩 Schema Snapshot")
        st.write(audit["schema_snapshot"]["current_state"])
        for i in audit["schema_snapshot"]["recommended_focus"]:
            st.write(f"- {i}")

        st.subheader("🧠 Entity Readiness")
        st.write(audit["entity_readiness"]["assessment"])
        for i in audit["entity_readiness"]["gaps"]:
            st.write(f"- {i}")

        st.subheader("📚 Citation Readiness")
        st.write(audit["citation_readiness"]["assessment"])
        for i in audit["citation_readiness"]["gaps"]:
            st.write(f"- {i}")

        st.subheader("✅ Priority Actions")
        for i in audit["priority_actions"]:
            st.write(f"- {i}")

        st.download_button(
            "⬇️ Download GEO Audit (JSON)",
            json.dumps(audit, indent=2),
            "geo_audit.json",
            "application/json",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Audit failed: {str(e)}")
