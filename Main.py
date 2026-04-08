import streamlit as st

st.set_page_config(
    page_title="GEO Workflow",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 GEO Optimisation Workflow")
st.write(
    "Run a complete **Generative Engine Optimisation (GEO)** pipeline from a single URL. "
    "All tools share the same analysis context."
)

# ============================================================
# INITIALISE SHARED GEO CONTEXT
# ============================================================
if "geo_context" not in st.session_state:
    st.session_state.geo_context = {}

# ============================================================
# INPUTS (ONCE)
# ============================================================
st.subheader("1️⃣ Business & Website Input")

url = st.text_input("Website URL", placeholder="https://example.com")

company_name = st.text_input("Company name")
industry = st.text_input("Industry / category")
niche = st.text_input("Niche (e.g. 'sensitive skin care')")
target_customer = st.text_input("Target customer")
goal = st.text_area("What do you want AI to recommend or explain?", height=80)

external_visibility = st.text_area(
    "External AI visibility metrics (optional)",
    placeholder="Paste metrics from Profound, Amplitude, etc.",
    height=100
)

run = st.button("▶️ Run GEO Workflow", type="primary", use_container_width=True)

# ============================================================
# RUN WORKFLOW
# ============================================================
if run:
    if not url.startswith("http"):
        st.error("Please enter a valid URL.")
        st.stop()

    # Build GEO context once
    st.session_state.geo_context = {
        "url": url,
        "company": {
            "name": company_name,
            "industry": industry,
            "niche": niche,
            "target_customer": target_customer,
            "goal": goal,
        },
        "external_visibility": external_visibility,
        "target_prompts": [],
        "audit": {},
        "entities": {},
        "rewritten_content": "",
        "schema": {},
        "mock_html": "",
        "implementation": {}
    }

    st.success("GEO job initialised ✅")
    st.info("Use the sidebar to step through Audit → Entities → Content → Schema → Preview → Implementation.")

``
