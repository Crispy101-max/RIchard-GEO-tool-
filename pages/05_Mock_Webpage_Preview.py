import streamlit as st

if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please initialise a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

import streamlit as st
import streamlit.components.v1 as components
import re

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Mock Webpage Preview",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Mock Webpage Preview")
st.write(
    "Visualise a **clean, AI‑readable webpage structure** based on "
    "existing or GEO‑optimised content. This is a structural preview, "
    "not a production design."
)

# ============================================================
# INPUT
# ============================================================
content = st.text_area(
    "Paste rewritten / optimised content",
    height=320,
    placeholder="Paste GEO‑optimised content here..."
)

run = st.button("Generate Mock Webpage", type="primary", use_container_width=True)

# ============================================================
# HELPERS
# ============================================================
def simple_markdown_to_html(text: str) -> str:
    text = text.strip()
    lines = text.split("\n")
    html = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("### "):
            html.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            html.append(f"<li>{line[2:]}</li>")
        else:
            html.append(f"<p>{line}</p>")

    final = []
    in_list = False
    for item in html:
        if item.startswith("<li>"):
            if not in_list:
                final.append("<ul>")
                in_list = True
            final.append(item)
        else:
            if in_list:
                final.append("</ul>")
                in_list = False
            final.append(item)
    if in_list:
        final.append("</ul>")

    return "\n".join(final)


def wrap_html(content_html: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>GEO Mock Webpage</title>
<style>
body {{
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    background: #0f172a;
    color: #e5e7eb;
    line-height: 1.6;
}}
.container {{
    max-width: 960px;
    margin: 0 auto;
    padding: 32px;
}}
.card {{
    background: #1e293b;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 30px 60px rgba(0,0,0,.35);
}}
h1, h2, h3 {{
    color: white;
    margin-top: 24px;
}}
h1 {{
    font-size: 2.6rem;
}}
h2 {{
    font-size: 1.8rem;
}}
p {{
    color: #cbd5f5;
    margin-bottom: 14px;
}}
ul {{
    padding-left: 22px;
}}
li {{
    margin-bottom: 8px;
}}
.badge {{
    display: inline-block;
    background: rgba(99,102,241,.2);
    color: #c7d2fe;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: .85rem;
    margin-bottom: 16px;
}}
footer {{
    margin-top: 56px;
    text-align: center;
    color: #94a3b8;
    font-size: .9rem;
}}
</style>
</head>
<body>
<div class="container">
    <div class="card">
        <span class="badge">GEO content structure preview</span>
        {content_html}
    </div>
    <footer>
        This mockup visualises structure & clarity for AI understanding — not final design.
    </footer>
</div>
</body>
</html>
"""


# ============================================================
# MAIN
# ============================================================
if run:
    if not content.strip():
        st.error("Please paste some content to visualise.")
        st.stop()

    html_body = simple_markdown_to_html(content)
    html_page = wrap_html(html_body)

    st.subheader("🔍 Live Preview")
    components.html(html_page, height=1400, scrolling=True)

    st.download_button(
        "⬇️ Download HTML Mockup",
        html_page,
        "geo_mock_webpage.html",
        "text/html",
        use_container_width=True
    )
