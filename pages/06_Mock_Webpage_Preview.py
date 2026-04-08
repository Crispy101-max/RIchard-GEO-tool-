import re
import html
import streamlit as st
import streamlit.components.v1 as components

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
    "Generate a real, scrollable mock webpage from the rewritten GEO content. "
    "You can preview it, copy the HTML, and download it."
)

# ============================================================
# GEO CONTEXT GUARD
# ============================================================
if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please start a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

# ============================================================
# LOAD CONTEXT SAFELY
# ============================================================
company = geo.get("company", {}) or {}
page_snapshot = geo.get("page_snapshot", {}) or {}
rewritten_content = geo.get("rewritten_content", "") or ""
target_prompts = geo.get("target_prompts", []) or []

brand_name = company.get("name", "") or page_snapshot.get("brand_name", "") or "Brand"
page_title_value = page_snapshot.get("title", "") or "Optimised Webpage"
meta_description = page_snapshot.get("meta_description", "") or ""
headings = page_snapshot.get("headings", []) or []

if not rewritten_content:
    st.warning("No rewritten content found yet. Run the GEO Content Optimiser first.")
    st.stop()

# ============================================================
# HELPERS
# ============================================================
def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text or "section"


def escape_text(text):
    return html.escape(text or "")


def parse_markdown_sections(text):
    """
    Converts rewritten markdown-like content into structured sections.
    Expected patterns:
    # Main title
    ## Section
    ### Subsection
    - bullet
    plain paragraph
    """
    lines = text.split("\n")
    sections = []
    current = {
        "title": "",
        "content": []
    }
    page_title = ""
    intro_paragraphs = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("# "):
            if not page_title:
                page_title = line[2:].strip()
            else:
                if current["title"] or current["content"]:
                    sections.append(current)
                current = {
                    "title": line[2:].strip(),
                    "content": []
                }

        elif line.startswith("## "):
            if current["title"] or current["content"]:
                sections.append(current)
            current = {
                "title": line[3:].strip(),
                "content": []
            }

        elif line.startswith("### "):
            current["content"].append(("h3", line[4:].strip()))

        elif line.startswith("- "):
            current["content"].append(("li", line[2:].strip()))

        else:
            if not current["title"] and not sections and not page_title:
                intro_paragraphs.append(line)
            else:
                current["content"].append(("p", line))

    if current["title"] or current["content"]:
        sections.append(current)

    return {
        "page_title": page_title,
        "intro": intro_paragraphs,
        "sections": sections
    }


def render_section_content(content_items):
    html_parts = []
    in_list = False

    for kind, text in content_items:
        safe = escape_text(text)

        if kind == "li":
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{safe}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False

            if kind == "h3":
                html_parts.append(f"<h3>{safe}</h3>")
            else:
                html_parts.append(f"<p>{safe}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def build_mock_webpage_html(brand_name, page_title_value, meta_description, headings, target_prompts, rewritten_content):
    parsed = parse_markdown_sections(rewritten_content)

    hero_title = parsed["page_title"] or page_title_value or "Optimised Page"
    intro = parsed["intro"]
    sections = parsed["sections"]

    # Hero intro text
    hero_text = ""
    if intro:
        hero_text = " ".join(intro[:2])
    elif meta_description:
        hero_text = meta_description
    else:
        hero_text = (
            "This mock webpage shows what a more structured, human-friendly, "
            "AI-readable version of the page could look like."
        )

    # Navigation
    nav_labels = []
    for sec in sections[:6]:
        if sec["title"]:
            nav_labels.append(sec["title"])
    if not nav_labels:
        nav_labels = headings[:6]
    if not nav_labels:
        nav_labels = ["Overview", "Benefits", "Details", "FAQs", "Contact"]

    nav_html = "".join(
        [f'<a href="#{slugify(label)}">{escape_text(label)}</a>' for label in nav_labels]
    )

    # Prompt chips
    prompt_chips = "".join(
        [f'<span class="chip">{escape_text(p)}</span>' for p in target_prompts[:6]]
    )

    # Main sections
    section_html = []
    for idx, sec in enumerate(sections):
        title = sec["title"] or f"Section {idx + 1}"
        anchor = slugify(title)
        body_html = render_section_content(sec["content"])

        section_html.append(f"""
        <section id="{anchor}" class="content-section">
            <div class="section-card">
                <div class="section-header">
                    <span class="section-label">Optimised section</span>
                    <h2>{escape_text(title)}</h2>
                </div>
                <div class="section-body">
                    {body_html}
                </div>
            </div>
        </section>
        """)

    if not section_html:
        fallback_body = render_section_content([("p", rewritten_content)])
        section_html.append(f"""
        <section id="overview" class="content-section">
            <div class="section-card">
                <div class="section-header">
                    <span class="section-label">Optimised section</span>
                    <h2>Overview</h2>
                </div>
                <div class="section-body">
                    {fallback_body}
                </div>
            </div>
        </section>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{escape_text(hero_title)}</title>
<style>
:root {{
  --bg: #0f172a;
  --surface: #111827;
  --panel: #1f2937;
  --panel-2: #243244;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --accent: #6366f1;
  --accent-2: #22c55e;
  --border: rgba(255,255,255,0.08);
  --shadow: 0 25px 60px rgba(0,0,0,.28);
}}
* {{
  box-sizing: border-box;
}}
html {{
  scroll-behavior: smooth;
}}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: linear-gradient(180deg, var(--bg), #111827);
  color: var(--text);
  line-height: 1.6;
}}
.container {{
  width: min(1140px, calc(100% - 32px));
  margin: 0 auto;
}}
.nav {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
}}
.nav-inner {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
  gap: 20px;
}}
.brand {{
  font-weight: 700;
  color: white;
  font-size: 1.05rem;
}}
.nav-links {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}}
.nav-links a {{
  color: var(--muted);
  text-decoration: none;
  font-size: .92rem;
}}
.nav-links a:hover {{
  color: white;
}}
.hero {{
  padding: 72px 0 32px;
}}
.hero-card {{
  border-radius: 28px;
  padding: 42px;
  border: 1px solid var(--border);
  background:
    radial-gradient(circle at top left, rgba(99,102,241,.18), transparent 35%),
    linear-gradient(135deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  box-shadow: var(--shadow);
}}
.eyebrow {{
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(99,102,241,.18);
  color: #c7d2fe;
  font-size: .85rem;
  margin-bottom: 16px;
}}
.hero h1 {{
  font-size: clamp(2rem, 5vw, 3.8rem);
  line-height: 1.05;
  margin: 0 0 14px;
  color: white;
}}
.hero p {{
  max-width: 820px;
  margin: 0 0 22px;
  color: var(--muted);
  font-size: 1.02rem;
}}
.hero-actions {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}}
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14px 22px;
  border-radius: 14px;
  text-decoration: none;
  font-weight: 600;
}}
.btn-primary {{
  background: var(--accent);
  color: white;
}}
.btn-secondary {{
  background: rgba(255,255,255,.05);
  color: var(--text);
  border: 1px solid var(--border);
}}
.summary-grid {{
  display: grid;
  gap: 18px;
  grid-template-columns: 1.2fr 1fr;
  padding: 24px 0 20px;
}}
.summary-card {{
  background: var(--panel);
  border-radius: 20px;
  padding: 22px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}}
.summary-card h3 {{
  margin-top: 0;
  color: white;
}}
.chips {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.chip {{
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,.06);
  border: 1px solid var(--border);
  color: #dbeafe;
  font-size: .85rem;
}}
.main-grid {{
  display: grid;
  gap: 22px;
  grid-template-columns: 2fr 1fr;
  padding-bottom: 56px;
}}
.content-section {{
  margin-bottom: 20px;
}}
.section-card {{
  background: var(--panel);
  border-radius: 22px;
  padding: 28px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}}
.section-label {{
  display: inline-block;
  margin-bottom: 10px;
  color: #c7d2fe;
  font-size: .84rem;
}}
.section-card h2 {{
  margin: 0 0 14px;
  color: white;
}}
.section-card h3 {{
  margin-top: 20px;
  color: white;
}}
.section-card p {{
  color: #cbd5e1;
  margin: 0 0 14px;
}}
.section-card ul {{
  padding-left: 22px;
}}
.section-card li {{
  margin-bottom: 8px;
  color: #cbd5e1;
}}
.sidebar-card {{
  background: var(--panel-2);
  border-radius: 20px;
  padding: 22px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}}
.sidebar-card h3 {{
  margin-top: 0;
  color: white;
}}
.sidebar-card p {{
  color: var(--muted);
}}
.footer {{
  padding: 18px 0 56px;
  text-align: center;
  color: var(--muted);
}}
@media (max-width: 960px) {{
  .summary-grid,
  .main-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>
</head>
<body>

<nav class="nav">
  <div class="container nav-inner">
    <div class="brand">{escape_text(brand_name)}</div>
    <div class="nav-links">
      {nav_html}
    </div>
  </div>
</nav>

<header class="hero">
  <div class="container">
    <div class="hero-card">
      <div class="eyebrow">Optimised webpage concept</div>
      <h1>{escape_text(hero_title)}</h1>
      <p>{escape_text(hero_text)}</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="#main-content">Explore page</a>
        <a class="btn btn-secondary" href="#top-prompts">View target prompts</a>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <h3>What this mockup is showing</h3>
        <p>
          This preview turns the rewritten GEO content into a more structured, more readable,
          more recommendation-ready webpage concept. It is designed to feel like a real client page,
          not just a wall of text.
        </p>
      </div>

      <div class="summary-card" id="top-prompts">
        <h3>Target prompts</h3>
        <div class="chips">
          {prompt_chips if prompt_chips else '<span class="chip">No prompts found yet</span>'}
        </div>
      </div>
    </div>
  </div>
</header>

<main class="container main-grid" id="main-content">
  <div>
    {''.join(section_html)}
  </div>

  <aside>
    <div class="sidebar-card">
      <h3>Why this version is stronger</h3>
      <p>
        Clearer section hierarchy, better scannability, stronger call-to-action placement,
        and a more believable page rhythm for both humans and AI systems.
      </p>
    </div>

    <div class="sidebar-card">
      <h3>Client-facing use</h3>
      <p>
        Use this mockup to show the client what a better structured, more recommendation-ready
        webpage could look like before implementation.
      </p>
    </div>
  </aside>
</main>

<footer class="footer">
  <div class="container">
    Mock webpage preview generated from the GEO workflow.
  </div>
</footer>

</body>
</html>
"""


# ============================================================
# BUILD HTML
# ============================================================
html_page = build_mock_webpage_html(
    brand_name=brand_name,
    page_title_value=page_title_value,
    meta_description=meta_description,
    headings=headings,
    target_prompts=target_prompts,
    rewritten_content=rewritten_content
)

geo["mock_html"] = html_page
st.session_state.geo_context = geo

# ============================================================
# DISPLAY
# ============================================================
st.subheader("🏢 Company Context")
st.write(f"**Company:** {brand_name}")
st.write(f"**Industry:** {company.get('industry', '')}")
st.write(f"**Niche:** {company.get('niche', '')}")

st.subheader("🎯 Source")
st.write(f"**Page title:** {page_title_value}")

st.subheader("🌐 Live Scrollable Website Preview")
components.html(html_page, height=1700, scrolling=True)

st.subheader("👨‍💻 HTML Code")
st.caption("Copy the full HTML below or download it as a file.")
st.text_area("HTML Output", html_page, height=420)

st.download_button(
    "⬇️ Download HTML File",
    html_page,
    "geo_mock_website.html",
    "text/html",
    use_container_width=True
)
