import streamlit as st
import streamlit.components.v1 as components
from geo_shared import ensure_geo_context, simple_markdown_to_html, build_mock_html

st.set_page_config(
    page_title="Mock Webpage Preview",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Mock Webpage Preview")
st.write(
    "Generate a **real scrollable webpage mockup** from the rewritten GEO content. "
    "You can preview it, copy the HTML, and download it for client presentation."
)

geo = ensure_geo_context()

company = geo.get("company", {})
page_snapshot = geo.get("page_snapshot", {})
rewritten_content = geo.get("rewritten_content", "")

page_title_value = page_snapshot.get("title", "GEO Mockup")

if not rewritten_content:
    st.warning("No rewritten content found yet. Run the GEO Content Optimiser first.")
    st.stop()

st.subheader("🏢 Company Context")
st.write(f"**Company:** {company.get('name', '')}")
st.write(f"**Industry:** {company.get('industry', '')}")
st.write(f"**Niche:** {company.get('niche', '')}")

st.subheader("🎯 Source")
st.write(f"**Page title:** {page_title_value}")

content_html = simple_markdown_to_html(rewritten_content)
html_page = build_mock_html(
    title=page_title_value,
    badge="GEO content structure preview",
    content_html=content_html
)

geo["mock_html"] = html_page
st.session_state.geo_context = geo

st.subheader("🌐 Live Scrollable Website Preview")
components.html(html_page, height=1600, scrolling=True)

st.subheader("👨‍💻 HTML Code")
st.caption("Use the box below to copy the full HTML easily and send it to clients or developers.")
st.text_area("HTML Output", html_page, height=420)

st.download_button(
    "⬇️ Download HTML File",
    html_page,
    "geo_mock_website.html",
    "text/html",
    use_container_width=True
)
