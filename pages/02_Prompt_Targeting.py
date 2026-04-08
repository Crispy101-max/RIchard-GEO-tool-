import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(page_title="Prompt Targeting", page_icon="🎯", layout="wide")
st.title("🎯 Prompt & Intent Targeting")
st.write(
    "Review or regenerate the AI prompts this client should be optimising around."
)

st.subheader("Current Business Context")
st.write(f"**Company:** {geo['company'].get('name', '')}")
st.write(f"**Industry:** {geo['company'].get('industry', '')}")
st.write(f"**Niche:** {geo['company'].get('niche', '')}")
st.write(f"**Target customer:** {geo['company'].get('target_customer', '')}")
st.write(f"**Goal:** {geo['company'].get('goal', '')}")

run = st.button("Generate / Refresh Target Prompts", type="primary", use_container_width=True)

if run or not geo.get("prompt_targeting"):
    client = get_client()

    SYSTEM_PROMPT = """
You are an AI discovery strategist.

Generate the AI prompts this business should be trying to win in ChatGPT, Copilot,
Gemini, and Perplexity.

Focus on:
- recommendation prompts
- 'best X for Y' prompts
- problem / solution prompts
- comparison prompts
- buyer selection prompts

Do NOT invent unsupported claims.

Return JSON ONLY in this structure:
{
  "summary": "",
  "core_prompts": [],
  "supporting_prompts": [],
  "buyer_journey_prompts": [],
  "why_these_prompts_matter": []
}
"""

    USER_PROMPT = f"""
COMPANY:
{geo["company"]}

PAGE SNAPSHOT:
{geo["page_snapshot"]}
"""

    with st.spinner("Generating target prompts..."):
        result = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)

    geo["prompt_targeting"] = result
    geo["target_prompts"] = result.get("core_prompts", []) + result.get("supporting_prompts", [])
    st.session_state.geo_context = geo

pt = geo.get("prompt_targeting", {})

if pt:
    st.subheader("🧠 Summary")
    st.write(pt.get("summary", ""))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Core Prompts")
        for item in pt.get("core_prompts", []):
            st.write(f"- {item}")

        st.subheader("🛒 Buyer Journey Prompts")
        for item in pt.get("buyer_journey_prompts", []):
            st.write(f"- {item}")

    with col2:
        st.subheader("📌 Supporting Prompts")
        for item in pt.get("supporting_prompts", []):
            st.write(f"- {item}")

        st.subheader("💡 Why These Matter")
        for item in pt.get("why_these_prompts_matter", []):
            st.write(f"- {item}")
