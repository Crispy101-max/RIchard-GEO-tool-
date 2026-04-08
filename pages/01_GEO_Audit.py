import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Audit",
    page_icon="📋",
    layout="wide"
)

st.title("📋 GEO Audit")

# ============================================================
# SHARED CONTEXT GUARD
# ============================================================
if "geo_context" not in st.session_state:
    st.warning("Please start a GEO job from the Main page first.")
    st.stop()

geo = st.session_state.geo_context

# ============================================================
# BASIC CONTEXT DISPLAY
# ============================================================
st.subheader("🔗 Website")
st.write(geo.get("url", "No URL found"))

company = geo.get("company", {}) or {}

st.subheader("🏢 Company")
st.write(f"Name: {company.get('name', 'N/A')}")
st.write(f"Industry: {company.get('industry', 'N/A')}")
st.write(f"Niche: {company.get('niche', 'N/A')}")
st.write(f"Target customer: {company.get('target_customer', 'N/A')}")
st.write(f"Goal: {company.get('goal', 'N/A')}")

prompts = geo.get("target_prompts", [])

st.subheader("🎯 Target AI Prompts")
if prompts:
    for p in prompts:
        st.write(f"- {p}")
else:
    st.write("No prompts defined yet.")

# ============================================================
# PLACEHOLDER AUDIT (SAFE)
# ============================================================
st.divider()
st.subheader("✅ Audit Status")

st.info(
    "This is a safe placeholder GEO Audit page. "
    "The advanced interactive audit will be reintroduced once the app is stable."
)

st.success("✅ GEO Audit page loaded successfully without syntax errors.")
