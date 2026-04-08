import json
import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

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
    "Rewrite the page so it is clearer, more explicit, and more likely to be recommended "
    "for the target AI prompts."
)

# ============================================================
# GEO CONTEXT
# ============================================================
geo = ensure_geo_context()

# ============================================================
# LOAD CONTEXT
# ============================================================
company = geo.get("company", {})
target_prompts = geo.get("target_prompts", [])
audit = geo.get("audit", {})
entities = geo.get("entities", {})
snapshot = geo.get("page_snapshot", {})

# ============================================================
# PAGE HEADER
# ============================================================
st.subheader("🏢 Company Context")
st.write(f"**Company:** {company.get('name', '')}")
st.write(f"**Industry:** {company.get('industry', '')}")
st.write(f"**Niche:** {company.get('niche', '')}")
st.write(f"**Target customer:** {company.get('target_customer', '')}")
st.write(f"**Goal:** {company.get('goal', '')}")

st.subheader("🎯 Target AI Prompts")
if target_prompts:
    for prompt in target_prompts:
        st.write(f"- {prompt}")
else:
    st.warning("No target prompts found yet. Run Prompt Targeting first.")

st.subheader("📄 Source Page Snapshot")
st.write(f"**Title:** {snapshot.get('title', '')}")
st.write(f"**Meta description:** {snapshot.get('meta_description', '')}")

# ============================================================
# BUTTON
# ============================================================
run = st.button("Run / Refresh Content Optimiser", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
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

# ============================================================
# RUN OPTIMISER
# ============================================================
if run or not geo.get("rewritten_content"):
    client = get_client()

    user_prompt = f"""
COMPANY:
{json.dumps(company, ensure_ascii=False)}

TARGET PROMPTS:
{json.dumps(target_prompts, ensure_ascii=False)}

AUDIT:
{json.dumps(audit, ensure_ascii=False)}

ENTITIES:
{json.dumps(entities, ensure_ascii=False)}

SOURCE PAGE SNAPSHOT:
{json.dumps(snapshot, ensure_ascii=False)}
"""

    try:
        with st.spinner("Optimising content for GEO..."):
            result = call_gemini_json(client, SYSTEM_PROMPT, user_prompt)

        geo["rewritten_content"] = result.get("rewritten_content", "")
        geo["content_notes"] = result.get("notes", {})
        st.session_state.geo_context = geo

        st.success("✅ Rewritten content saved to shared GEO workflow context.")

    except Exception as e:
        st.error(f"Content optimisation failed: {str(e)}")

# ============================================================
# DISPLAY OUTPUT
# ============================================================
rewritten_content = geo.get("rewritten_content", "")
content_notes = geo.get("content_notes", {})

if rewritten_content:
    st.subheader("✅ Rewritten Content")
    st.text_area("Output", rewritten_content, height=420)

    st.download_button(
        "⬇️ Download Rewritten Content",
        data=rewritten_content,
        file_name="geo_rewritten_content.txt",
        mime="text/plain",
        use_container_width=True
    )

if content_notes:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("What changed")
        for item in content_notes.get("what_changed", []):
            st.write(f"- {item}")

    with col2:
        st.subheader("Remaining gaps")
        for item in content_notes.get("remaining_gaps", []):
            st.write(f"- {item}")
