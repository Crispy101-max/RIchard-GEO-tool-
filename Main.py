import streamlit as st
from geo_shared import get_client, fetch_page_snapshot, call_gemini_json

st.set_page_config(
    page_title="GEO Workflow",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 GEO Visibility Optimisation Workflow")
st.write(
    "Enter the website and client context once. The app will create a shared GEO job "
    "that all pages read from and write to."
)

if "geo_context" not in st.session_state:
    st.session_state.geo_context = {}

with st.form("geo_intake"):
    url = st.text_input("Website URL", placeholder="https://example.com")
    company_name = st.text_input("Company name")
    industry = st.text_input("Industry / category")
    niche = st.text_input("Niche", placeholder="e.g. sensitive skin care")
    target_customer = st.text_input("Target customer")
    goal = st.text_area(
        "What do you want AI to recommend or explain?",
        height=90,
        placeholder="e.g. be recommended for 'best cream for sensitive skin'"
    )
    external_visibility = st.text_area(
        "External AI visibility metrics (optional)",
        height=110,
        placeholder="Paste metrics from Profound, Amplitude, or another provider"
    )
    submitted = st.form_submit_button("▶️ Start / Refresh GEO Job", use_container_width=True)

if submitted:
    if not url.startswith("http"):
        st.error("Please enter a valid URL.")
        st.stop()

    with st.spinner("Fetching page snapshot..."):
        snapshot = fetch_page_snapshot(url)

    geo = {
        "url": url,
        "company": {
            "name": company_name,
            "industry": industry,
            "niche": niche,
            "target_customer": target_customer,
            "goal": goal,
        },
        "external_visibility": external_visibility,
        "page_snapshot": snapshot,
        "prompt_targeting": {},
        "target_prompts": [],
        "audit": {},
        "entities": {},
        "rewritten_content": "",
        "content_notes": {},
        "schema": {},
        "mock_html": "",
        "implementation": {},
    }

    # Generate initial target prompts immediately so downstream pages can use them
    client = get_client()

    SYSTEM_PROMPT = """
You are an AI discovery strategist.

Given a business and a current webpage, generate the AI prompts this business should
be trying to win in tools like ChatGPT, Copilot, Gemini, and Perplexity.

Focus on:
- recommendation prompts
- 'best X for Y' prompts
- problem/solution prompts
- comparison prompts
- decision prompts

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
{snapshot}
"""

    try:
        with st.spinner("Generating initial target prompts..."):
            prompt_targeting = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)

        geo["prompt_targeting"] = prompt_targeting
        geo["target_prompts"] = (
            prompt_targeting.get("core_prompts", []) +
            prompt_targeting.get("supporting_prompts", [])
        )
    except Exception:
        # Fail gracefully; page 02 can regenerate these
        geo["prompt_targeting"] = {
            "summary": "",
            "core_prompts": [],
            "supporting_prompts": [],
            "buyer_journey_prompts": [],
            "why_these_prompts_matter": []
        }
        geo["target_prompts"] = []

    st.session_state.geo_context = geo
    st.success("✅ GEO job initialised.")
    st.info("Use the sidebar pages in order: Audit → Prompts → Entities → Content → Schema → Mock → Implementation.")

geo = st.session_state.geo_context

if geo and "url" in geo:
    st.subheader("Current GEO Job")
    st.write(f"**URL:** {geo['url']}")
    st.write(f"**Company:** {geo['company'].get('name', '')}")
    st.write(f"**Niche:** {geo['company'].get('niche', '')}")
    st.write(f"**Target prompts generated:** {len(geo.get('target_prompts', []))}")
else:
    st.caption("No GEO job yet. Fill out the form above to begin.")
