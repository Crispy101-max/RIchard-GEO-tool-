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
    page_title="Mock Webpage Preview",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Mock Webpage Preview")
st.write(
    "This page visualises the rewritten content as a simple webpage structure."
)

content = geo.get("rewritten_content", "")

if not content:
    st.warning("No rewritten content found. Run the GEO Content Optimiser first.")
    st.stop()

# ------------------------------------------------------------
# SIMPLE, SAFE PREVIEW (NO HTML / NO COMPONENTS)
# ------------------------------------------------------------
st.subheader("🧱 Page Structure Preview")

lines = content.split("\n")

for line in lines:
    line = line.strip()

    if not line:
        continue

    if line.startswith("# "):
        st.header(line.replace("# ", ""))
    elif line.startswith("## "):
        st.subheader(line.replace("## ", ""))
    elif line.startswith("- "):
        st.markdown(f"- {line[2:]}")
    else:
        st.write(line)

# ------------------------------------------------------------
# SAVE MOCK STATE (OPTIONAL)
# ------------------------------------------------------------
geo["mock_html"] = content
st.session_state.geo_context = geo
