import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(page_title="GEO Audit", page_icon="📋", layout="wide")
st.title("📋 GEO Audit")
st.write(
    "Diagnose how well the current page is positioned for AI understanding and recommendation."
)

st.subheader("🎯 Target AI Prompts")
for p in geo.get("target_prompts", []):
    st.write(f"- {p}")
if not geo.get("target_prompts", []):
    st.caption("No target prompts yet — run Prompt Targeting to improve the audit.")

if geo.get("external_visibility"):
    st.subheader("📈 External Visibility Context")
    st.write(geo["external_visibility"])

run = st.button("Run / Refresh Audit", type="primary", use_container_width=True)

if run or not geo.get("audit"):
    client = get_client()

    SYSTEM_PROMPT = """
You are a senior Generative Engine Optimisation auditor.

Assess the page against the target AI prompts.

Focus on:
- AI readability and structure
- alignment with target prompts
- entity clarity
- citation readiness
- schema posture
- content gaps

Do NOT rewrite content.

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
  "priority_actions": []
}
"""

    USER_PROMPT = f"""
COMPANY:
{geo["company"]}

TARGET PROMPTS:
{geo.get("target_prompts", [])}

PAGE SNAPSHOT:
{geo["page_snapshot"]}

EXTERNAL VISIBILITY:
{geo.get("external_visibility", "")}
"""

    with st.spinner("Running GEO audit..."):
        geo["audit"] = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)
        st.session_state.geo_context = geo

audit = geo.get("audit", {})

if audit:
    st.subheader("🧠 Overall Summary")
    st.write(audit.get("overall_summary", ""))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("✅ Strengths")
        for item in audit.get("strengths", []):
            st.write(f"- {item}")

    with col2:
        st.subheader("❌ Weaknesses")
        for item in audit.get("weaknesses", []):
            st.write(f"- {item}")

    with col3:
        st.subheader("🚀 Opportunities")
        for item in audit.get("opportunities", []):
            st.write(f"- {item}")

    st.subheader("📈 Visibility Context")
    vc = audit.get("visibility_context", {})
    st.write(vc.get("summary", ""))
    st.write(vc.get("impact_on_priorities", ""))

    st.subheader("✅ Priority Actions")
    for item in audit.get("priority_actions", []):
        st.write(f"- {item}")
        
