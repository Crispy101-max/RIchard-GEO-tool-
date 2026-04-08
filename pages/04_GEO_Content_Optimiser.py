import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(
    page_title="GEO Content Optimiser",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ GEO Content Optimiser")
st.write(
    "Rewrite the page so it is clearer, more explicit, and more likely to be recommended "
    "for the target AI prompts."
)

st.subheader("🎯 Target AI Prompts")
target_prompts = geo.get("target_prompts", [])
if target_prompts:
    for p in target_prompts:
        st.write(f"- {p}")
else:
    st.warning("No target prompts found yet. Run Prompt Targeting first.")

run = st.button("Run / Refresh Content Optimiser", type="primary", use_container_width=True)

if run or not geo.get("rewritten_content"):
    client = get_client()

    system_prompt = """
You are a senior Generative Engine Optimisation content strategist.

Rewrite the page so it is easier for AI systems to understand and recommend.

Optimise for:
- answer-first structure
- explicit entity definitions
- alignment with target prompts
- clarity, trust, and chunking

Rules:
- Do NOT invent facts
- Preserve the original meaning and offer
- Use [DATA NEEDED: ...] where information is missing
- Return only valid JSON

Return JSON ONLY in this structure:
{
  "rewritten_content": "",
  "notes": {
    "what_changed": [],
    "remaining_gaps": []
  }
}
"""

    user_prompt = f"""
COMPANY:
{geo.get("company", {})}

TARGET PROMPTS:
{geo.get("target_prompts", [])}

AUDIT:
{geo.get("audit", {})}

ENTITIES:
{geo.get("entities", {})}

SOURCE PAGE:
{geo.get("page_snapshot", {})}
"""

    with st.spinner("Optimising content..."):
        result = call_gemini_json(client, system_prompt, user_prompt)

    geo["rewritten_content"] = result.get("rewritten_content", "")
    geo["content_notes"] = result.get("notes", {})
    st.session_state.geo_context = geo

st.subheader("✅ Rewritten Content")
st.text_area("Output", geo.get("rewritten_content", ""), height=420)

notes = geo.get("content_notes", {})
if notes:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("What changed")
        for item in notes.get("what_changed", []):
            st.write(f"- {item}")

    with col2:
        st.subheader("Remaining gaps")
        for item in notes.get("remaining_gaps", []):
            st.write(f"- {item}")
``
