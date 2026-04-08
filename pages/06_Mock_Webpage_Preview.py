import streamlit as st
import streamlit.components.v1 as components
from geo_shared import ensure_geo_context, simple_markdown_to_html, build_mock_html

geo = ensure_geo_context()

st.set_page_config(
    page_title="Mock Webpage Preview",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Mock Webpage Preview")
st.write(
    "Visualise the rewritten content as a clean webpage structure — no manual paste required."
)

content = geo.get("rewritten_content", "")

if not content:
    st.warning("No rewritten content yet. Run the GEO Content Optimiser first.")
    st.stop()

html_body = simple_markdown_to_html(content)

page_title = geo.get("page_snapshot", {}).get("title", "GEO Mockup")
html_page = build_mock_html(
    title=page_title,
    badge="GEO content structure preview",
    content_html=html_body
)

geo["mock_html"] = html_page
st.session_state.geo_context = geo

st.subheader("🔍 Live Preview")
components.html(html_page, height=1400, scrolling=True)

st.download_button(
    "⬇️ Download HTML Mockup",
    html_page,
    "geo_mock_webpage.html",
    "text/html",
    use_container_width=True
)
``
