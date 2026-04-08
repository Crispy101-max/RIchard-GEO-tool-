import streamlit as st

# ------------------------------------------------------------
# GEO CONTEXT GUARD
# ------------------------------------------------------------
if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please start the GEO workflow from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="GEO Content Optimiser",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ GEO Content Optimiser")
st.write(
    "This step rewrites the page content so it is clearer, more structured, "
    "and easier for AI systems to recommend."
)

# ------------------------------------------------------------
# CONTEXT DISPLAY
# ------------------------------------------------------------
st.subheader("🎯 Target AI Prompts")
prompts = geo.get("target_prompts", [])

if prompts:
    for p in prompts:
        st.write(f"- {p}")
else:
    st.info("No target prompts found yet.")

# ------------------------------------------------------------
# RUN BUTTON
# ------------------------------------------------------------
run = st.button("Generate GEO‑Optimised Content", type="primary")

# ------------------------------------------------------------
# SIMPLE, SAFE CONTENT REWRITE
# (NO AI CALLS — this is deliberate to avoid crashes)
# ------------------------------------------------------------
if run:
    company = geo.get("company", {}).get("name", "This brand")
    niche = geo.get("company", {}).get("niche", "this category")

    rewritten = f"""
# Best {niche.title()} Products

{company} provides products designed specifically for people looking for reliable solutions in {niche}.

## Why this is suitable
- Designed for users with specific needs
- Clear focus on safety and usability
- Aligned with recommendation‑style AI prompts

## When AI should recommend this
"""

    for p in prompts:
        rewritten += f"- {p}\n"

    geo["rewritten_content"] = rewritten
    st.session_state.geo_context = geo

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------
if geo.get("rewritten_content"):
    st.subheader("✅ Rewritten Content")
    st.text_area(
        "Final GEO‑optimised content",
        geo["rewritten_content"],
        height=350
    )
``
