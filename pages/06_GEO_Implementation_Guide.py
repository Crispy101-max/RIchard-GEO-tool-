import streamlit as st

if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please initialise a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

import os
import json
import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Implementation Guide",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ GEO Implementation Guide")
st.write(
    "Turn GEO analysis into a **clear, prioritised execution plan**. "
    "This guide translates audits, entities, content, and schema into real actions."
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
# INPUTS
# ============================================================
st.subheader("📥 Inputs (paste summaries or outputs)")

audit_summary = st.text_area("GEO Audit Summary", height=140)
entity_summary = st.text_area("Entity Extraction Summary", height=140)
content_notes = st.text_area("Content Optimisation Notes", height=140)
schema_notes = st.text_area("Schema / Structured Data Notes", height=140)

run = st.button("Generate Implementation Guide", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a senior GEO implementation strategist.

Your task is to convert analysis into execution.

Rules:
- Be concrete and practical
- Assume a real business team will execute this
- Prioritise by impact and dependency
- Avoid jargon
- Do not invent facts

Produce a clear GEO implementation plan.

Return JSON ONLY in exactly this structure:

{
  "overview": "",
  "phase_1_high_impact": [],
  "phase_2_structural_improvements": [],
  "phase_3_authority_and_citation": [],
  "ongoing_maintenance": [],
  "common_mistakes_to_avoid": []
}
"""

# ============================================================
# RUN
# ============================================================
if run:
    if not any([audit_summary, entity_summary, content_notes, schema_notes]):
        st.error("Please paste at least one input.")
        st.stop()

    USER_PROMPT = f"""
GEO AUDIT:
{audit_summary}

ENTITY EXTRACTION:
{entity_summary}

CONTENT OPTIMISATION:
{content_notes}

SCHEMA / STRUCTURED DATA:
{schema_notes}
"""

    with st.spinner("Generating implementation guide..."):
        response = client.models.generate_content(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                temperature=0,
                top_p=0.1,
                max_output_tokens=8192,
                seed=42,
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
            contents=USER_PROMPT,
        )

        guide = json.loads(response.text)

    st.success("Implementation guide generated")

    st.subheader("🧭 Overview")
    st.write(guide["overview"])

    st.subheader("🚀 Phase 1 — High‑Impact Actions")
    for i in guide["phase_1_high_impact"]:
        st.write(f"- {i}")

    st.subheader("🧱 Phase 2 — Structural Improvements")
    for i in guide["phase_2_structural_improvements"]:
        st.write(f"- {i}")

    st.subheader("📚 Phase 3 — Authority & Citation")
    for i in guide["phase_3_authority_and_citation"]:
        st.write(f"- {i}")

    st.subheader("🔁 Ongoing Maintenance")
    for i in guide["ongoing_maintenance"]:
        st.write(f"- {i}")

    st.subheader("⚠️ Common Mistakes to Avoid")
    for i in guide["common_mistakes_to_avoid"]:
        st.write(f"- {i}")

    st.download_button(
        "⬇️ Download Implementation Guide",
        json.dumps(guide, indent=2),
        "geo_implementation_guide.json",
        "application/json",
        use_container_width=True
    )
