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
    page_title="Entity Extraction",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Entity Extraction & Knowledge Graph Readiness")
st.write(
    "This tool identifies **entities present on a webpage**, evaluates how clearly they are defined, "
    "and highlights **entity gaps and optimisation opportunities** for Generative Engine Optimisation (GEO)."
)

# ============================================================
# API KEY / CLIENT
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
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@st.cache_data(show_spinner=False)
def extract_page(url: str):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]

    for el in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        el.decompose()

    text = clean(soup.get_text(separator=" ", strip=True))[:30000]

    return {
        "title": title,
        "headings": headings[:25],
        "text": text,
    }


def call_gemini(user_text: str, system_instruction: str):
    response = client.models.generate_content(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            max_output_tokens=8192,
            seed=42,
            system_instruction=system_instruction,
            response_mime_type="application/json",
        ),
        contents=user_text,
    )
    return json.loads(response.text)

# ============================================================
# INPUT
# ============================================================
url = st.text_input("Website page URL", placeholder="https://example.com/page")

run = st.button("Extract Entities", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a senior entity modeling and knowledge graph specialist.

Your task is to extract, classify, and evaluate entities from a webpage
for Generative Engine Optimisation (GEO).

Definitions:
- Entities are real, identifiable things: brands, products, services,
  people, organisations, concepts, locations, standards, tools, industries.

Rules:
- Only extract entities clearly present or strongly implied in the content.
- Do NOT invent or guess entities.
- Do NOT rewrite content.
- Avoid SEO jargon; be precise and analytical.

Classify entities into:
1. Primary entities (core subject of the page)
2. Secondary entities (supporting topics & concepts)
3. Supporting entities (locations, organisations, tools, standards)

Evaluate:
- How clearly entities are defined
- Whether relationships between entities are explicit
- Which important entities are missing
- How this affects GEO / AI understanding

Return JSON ONLY in exactly this structure:

{
  "entity_summary": "",
  "primary_entities": [],
  "secondary_entities": [],
  "supporting_entities": [],
  "entity_clarity_assessment": {
    "overall_clarity": "",
    "issues": []
  },
  "missing_or_weak_entities": [],
  "entity_relationship_gaps": [],
  "knowledge_graph_readiness": "",
  "priority_entity_actions": []
}
"""

# ============================================================
# RUN EXTRACTION
# ============================================================
if run:
    if not url.startswith("http"):
        st.error("Please enter a valid URL starting with http or https.")
        st.stop()

    try:
        with st.spinner("Reading webpage..."):
            page = extract_page(url)

        USER_PROMPT = f"""
URL:
{url}

PAGE TITLE:
{page["title"]}

HEADINGS:
{json.dumps(page["headings"], ensure_ascii=False)}

VISIBLE PAGE CONTENT:
{page["text"]}
"""

        with st.spinner("Extracting and analysing entities..."):
            entities = call_gemini(USER_PROMPT, SYSTEM_PROMPT)

        st.success("Entity extraction complete")

        # ====================================================
        # DISPLAY RESULTS
        # ====================================================
        st.subheader("🧾 Entity Summary")
        st.write(entities["entity_summary"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("🎯 Primary Entities")
            for e in entities["primary_entities"]:
                st.write(f"- {e}")

        with col2:
            st.subheader("🧩 Secondary Entities")
            for e in entities["secondary_entities"]:
                st.write(f"- {e}")

        with col3:
            st.subheader("📎 Supporting Entities")
            for e in entities["supporting_entities"]:
                st.write(f"- {e}")

        st.divider()

        st.subheader("🔍 Entity Clarity Assessment")
        st.write(entities["entity_clarity_assessment"]["overall_clarity"])

        if entities["entity_clarity_assessment"]["issues"]:
            st.write("**Issues detected:**")
            for i in entities["entity_clarity_assessment"]["issues"]:
                st.write(f"- {i}")

        st.subheader("❗ Missing or Weak Entities")
        for e in entities["missing_or_weak_entities"]:
            st.write(f"- {e}")

        st.subheader("🔗 Entity Relationship Gaps")
        for e in entities["entity_relationship_gaps"]:
            st.write(f"- {e}")

        st.subheader("🕸 Knowledge Graph Readiness")
        st.write(entities["knowledge_graph_readiness"])

        st.subheader("✅ Priority Entity Actions")
        for a in entities["priority_entity_actions"]:
            st.write(f"- {a}")

        st.download_button(
            "⬇️ Download Entity Report (JSON)",
            data=json.dumps(entities, indent=2),
            file_name="entity_extraction_report.json",
            mime="application/json",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Entity extraction failed: {str(e)}")
