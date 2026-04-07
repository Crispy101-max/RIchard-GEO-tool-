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
    "This audit assesses how well a webpage is positioned for **Generative Engine Optimisation (GEO)** — "
    "including AI readability, entity clarity, citation potential, schema posture, and content gaps."
)

# ============================================================
# API KEY
# ============================================================
def get_api_key() -> str:
    if "API_Key" in st.secrets:
        return st.secrets["API_Key"]
    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()
if not API_KEY:
    st.error("No Gemini API key found. Add it as `API_Key` in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-pro"

# ============================================================
# HELPERS
# ============================================================
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@st.cache_data(show_spinner=False)
def fetch_page(url: str):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_desc = ""
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        meta_desc = m["content"].strip()

    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]

    existing_schema = [
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
        "schema": existing_schema[:10],
    }


def call_gemini(user: str, system: str):
    response = client.models.generate_content(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            max_output_tokens=8192,
            seed=42,
            system_instruction=system,
            response_mime_type="application/json",
        ),
        contents=user,
    )
    return json.loads(response.text)

# ============================================================
# INPUT
# ============================================================
url = st.text_input("Website page URL", placeholder="https://example.com/page")

run = st.button("Run GEO Audit", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a senior Generative Engine Optimisation (GEO) auditor.

You must assess a webpage across dimensions that influence visibility, understanding,
and citation by AI systems (LLMs, answer engines, copilots).

You are NOT rewriting content.

You are identifying:
- strengths
- weaknesses
- high-impact GEO opportunities

Assess ALL of the following areas:
1. AI Readability & Structure
2. Content Intent & Page Purpose
3. Entity Definition & Knowledge Graph Alignment
4. Citation & Source Readiness
5. Schema Markup Posture (lightweight, advisory)
6. Content Gaps & Expansion Opportunities

Rules:
- Do not invent facts
- Base assessments strictly on visible content
- Be commercially realistic and conservative
- Avoid SEO jargon — write for decision-makers

Return JSON ONLY in exactly this structure:

{
  "overall_summary": "",
  "strengths": [],
  "weaknesses": [],
  "opportunities": [],
  "schema_snapshot": {
    "current_state": "",
    "recommended_focus": []
  },
  "content_structure_review": {
    "what_works": [],
    "what_breaks_ai_understanding": []
  },
  "entity_and_knowledge_graph": {
    "current_entity_clarity": "",
    "missing_entities_or_relationships": []
  },
  "citation_readiness": {
    "likelihood_of_being_cited": "",
    "missing_supporting_content": []
  },
  "priority_actions": []
}
"""

# ============================================================
# RUN AUDIT
# ============================================================
if run:
    if not url.startswith("http"):
        st.error("Please enter a valid URL starting with http or https.")
        st.stop()

    try:
        with st.spinner("Fetching webpage..."):
            page = fetch_page(url)

        USER_PROMPT = f"""
URL:
{url}

PAGE TITLE:
{page["title"]}

META DESCRIPTION:
{page["meta_description"]}

HEADINGS:
{json.dumps(page["headings"], ensure_ascii=False)}

VISIBLE PAGE CONTENT:
{page["text"]}

EXISTING SCHEMA (JSON-LD):
{json.dumps(page["schema"], ensure_ascii=False)}
"""

        with st.spinner("Running GEO audit..."):
            audit = call_gemini(USER_PROMPT, SYSTEM_PROMPT)

        st.success("GEO audit completed")

        # ====================================================
        # DISPLAY RESULTS
        # ====================================================
        st.subheader("🔎 Overall Summary")
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

        st.subheader("🧩 Schema Snapshot")
        st.write("**Current state:**", audit["schema_snapshot"]["current_state"])
        st.write("**Recommended focus:**")
        for i in audit["schema_snapshot"]["recommended_focus"]:
            st.write(f"- {i}")

        st.subheader("🧱 Content Structure Review")
        st.write("**What works:**")
        for i in audit["content_structure_review"]["what_works"]:
            st.write(f"- {i}")

        st.write("**What breaks AI understanding:**")
        for i in audit["content_structure_review"]["what_breaks_ai_understanding"]:
            st.write(f"- {i}")

        st.subheader("🧠 Entity & Knowledge Graph Optimisation")
        st.write(audit["entity_and_knowledge_graph"]["current_entity_clarity"])
        st.write("**Missing entities / relationships:**")
        for i in audit["entity_and_knowledge_graph"]["missing_entities_or_relationships"]:
            st.write(f"- {i}")

        st.subheader("📚 Citation & Source Readiness")
        st.write(audit["citation_readiness"]["likelihood_of_being_cited"])
        st.write("**Missing supporting content:**")
        for i in audit["citation_readiness"]["missing_supporting_content"]:
            st.write(f"- {i}")

        st.subheader("✅ Priority Actions")
        for i in audit["priority_actions"]:
            st.write(f"- {i}")

        st.download_button(
            "⬇️ Download GEO Audit (JSON)",
            data=json.dumps(audit, indent=2),
            file_name="geo_audit.json",
            mime="application/json",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Audit failed: {str(e)}")
``
