import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(page_title="GEO Implementation Guide", page_icon="🛠️", layout="wide")
st.title("🛠️ GEO Implementation Guide")
st.write(
    "Turn the GEO workflow outputs into a practical, prioritised execution plan."
)

run = st.button("Generate / Refresh Implementation Guide", type="primary", use_container_width=True)

if run or not geo.get("implementation"):
    client = get_client()

    SYSTEM_PROMPT = """
You are a GEO implementation strategist.

Create a practical plan from the workflow outputs.

Prioritise by:
- impact on AI visibility
- ease of implementation
- dependency order

Return JSON ONLY in this structure:
{
  "overview": "",
  "phase_1_high_impact": [],
  "phase_2_structural_improvements": [],
  "phase_3_authority_and_citation": [],
  "ongoing_maintenance": [],
  "common_mistakes_to_avoid": []
}
"""

    USER_PROMPT = f"""
COMPANY:
{geo["company"]}

TARGET PROMPTS:
{geo.get("target_prompts", [])}

AUDIT:
{geo.get("audit", {})}

ENTITIES:
{geo.get("entities", {})}

REWRITTEN CONTENT:
{geo.get("rewritten_content", "")[:8000]}

SCHEMA:
{geo.get("schema", {})}

EXTERNAL VISIBILITY:
{geo.get("external_visibility", "")}
"""

    with st.spinner("Generating implementation guide..."):
        geo["implementation"] = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)
        st.session_state.geo_context = geo

guide = geo.get("implementation", {})

if guide:
    st.subheader("🧭 Overview")
    st.write(guide.get("overview", ""))

    st.subheader("🚀 Phase 1 — High‑Impact Actions")
    for item in guide.get("phase_1_high_impact", []):
        st.write(f"- {item}")

    st.subheader("🧱 Phase 2 — Structural Improvements")
    for item in guide.get("phase_2_structural_improvements", []):
        st.write(f"- {item}")

    st.subheader("📚 Phase 3 — Authority & Citation")
    for item in guide.get("phase_3_authority_and_citation", []):
        st.write(f"- {item}")

    st.subheader("🔁 Ongoing Maintenance")
    for item in guide.get("ongoing_maintenance", []):
        st.write(f"- {item}")

    st.subheader("⚠️ Common Mistakes to Avoid")
    for item in guide.get("common_mistakes_to_avoid", []):
        st.write(f"- {item}")
