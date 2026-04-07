import streamlit as st

st.set_page_config(
    page_title="GEO Workbench",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 GEO Workbench")
st.write(
    "This is a **Generative Engine Optimisation (GEO) toolkit** for analysing, "
    "rewriting, structuring, and marking up webpages so they are clearer for AI systems, search engines, "
    "and citation-based discovery."
)

st.markdown("## Available Tools")
st.markdown("""
### 📝 GEO Content Optimiser
Rewrite an existing webpage so it is:
- easier for AI systems to understand and cite
- clearer, better structured, and more explicit
- visualised as a realistic webpage mockup

Use this when you want to **improve the actual page copy**.

---

### 🧩 Schema Strategy & Optimisation *(coming / separate tool)*
Analyse and improve structured data (JSON‑LD):
- clean up existing schema
- decide what schema is appropriate
- align schema with page content and business intent

Use this when you want to **improve machine‑readable meaning**.

---
""")

st.info("Use the left sidebar to open each tool.")

st.caption(
    "This app is designed as a multi‑step GEO workflow. "
    "Each tool focuses on one job so the system stays clean, powerful, and extensible."
)
