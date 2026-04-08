import os
import re
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

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
    "Generate a **real, scrollable website prototype** from the rewritten GEO content "
    "using structure and theme clues from the original page."
)

# ============================================================
# GEO CONTEXT
# ============================================================
if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please start a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context
rewritten_content = geo.get("rewritten_content", "")
if not rewritten_content:
    st.warning("No rewritten content found yet. Run the GEO Content Optimiser first.")
    st.stop()

# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key():
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass
    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()
if not API_KEY:
    st.error("No Gemini API key found. Add it as `API_Key` in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-pro"

# ============================================================
# HELPERS
# ============================================================
HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_hex_colours(html):
    colours = HEX_PATTERN.findall(html or "")
    seen = set()
    ordered = []
    for c in colours:
        c = c.lower()
        if len(c) == 4:
            c = "#" + "".join(ch * 2 for ch in c[1:])
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered[:8]


def page_snapshot(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else "Website"
    meta = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta = meta_tag["content"].strip()

    nav_items = []
    nav = soup.find("nav")
    if nav:
        for a in nav.find_all("a"):
            txt = clean(a.get_text(" ", strip=True))
            if txt and len(txt) < 30:
                nav_items.append(txt)

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = clean(tag.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    colours = extract_hex_colours(r.text)

    return {
        "title": title,
        "meta_description": meta,
        "nav_items": nav_items[:6],
        "headings": headings[:20],
        "colours": colours
    }


def clean_html_output(html_raw):
    html_raw = html_raw.strip()
    if html_raw.startswith("```"):
        html_raw = re.sub(r"^```(?:html)?\s*", "", html_raw)
        html_raw = re.sub(r"\s*```$", "", html_raw)
    return html_raw.strip()


def html_looks_valid(html_raw):
    h = html_raw.strip().lower()
    return h.startswith("<!doctype html") or h.startswith("<html")


def fallback_html(title, brand, nav_items, content):
    safe = (
        content.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    sections = []
    for line in safe.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("### "):
            sections.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            sections.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            sections.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            sections.append(f"<li>{line[2:]}</li>")
        else:
            sections.append(f"<p>{line}</p>")

    parsed = []
    in_list = False
    for item in sections:
        if item.startswith("<li>"):
            if not in_list:
                parsed.append("<ul>")
                in_list = True
            parsed.append(item)
        else:
            if in_list:
                parsed.append("</ul>")
                in_list = False
            parsed.append(item)
    if in_list:
        parsed.append("</ul>")

    nav_html = "".join([f"<a href='#'>{i}</a>" for i in nav_items]) if nav_items else "<a href='#'>Overview</a><a href='#'>Benefits</a><a href='#'>FAQs</a><a href='#'>Contact</a>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
:root {{
  --bg: #0f172a;
  --surface: #111827;
  --panel: #1f2937;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --accent: #6366f1;
  --accent2: #22c55e;
  --shadow: 0 25px 60px rgba(0,0,0,.28);
}}
* {{ box-sizing: border-box; }}
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
  z-index: 20;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255,255,255,.08);
}}
.nav-inner {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
}}
.brand {{
  font-weight: 700;
  color: white;
}}
.links {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}}
.links a {{
  color: var(--muted);
  text-decoration: none;
  font-size: .95rem;
}}
.hero {{
  padding: 72px 0 36px;
}}
.hero-card {{
  padding: 42px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(99,102,241,.18), transparent 35%),
    linear-gradient(135deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border: 1px solid rgba(255,255,255,.08);
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
  font-size: clamp(2rem, 5vw, 3.7rem);
  line-height: 1.05;
  margin: 0 0 12px;
  color: white;
}}
.hero p {{
  max-width: 780px;
  color: var(--muted);
  margin: 0 0 22px;
}}
.cta-row {{
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
  font-weight: 600;
  text-decoration: none;
}}
.btn-primary {{
  background: var(--accent);
  color: white;
}}
.btn-secondary {{
  background: rgba(255,255,255,.06);
  color: var(--text);
  border: 1px solid rgba(255,255,255,.08);
}}
.grid {{
  display: grid;
  gap: 20px;
  grid-template-columns: 2fr 1fr;
  padding: 14px 0 56px;
}}
.panel {{
  background: var(--panel);
  border-radius: 20px;
  padding: 28px;
  border: 1px solid rgba(255,255,255,.08);
  box-shadow: var(--shadow);
}}
.panel h2, .panel h3 {{
  color: white;
}}
.panel p {{
  color: #cbd5e1;
}}
.panel ul {{
  padding-left: 22px;
}}
.panel li {{
  margin-bottom: 8px;
}}
.side-card {{
  margin-bottom: 20px;
}}
.badge-card {{
  display: grid;
  gap: 12px;
}}
.badge {{
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.08);
  color: #dbeafe;
}}
.footer {{
  padding: 16px 0 56px;
  color: var(--muted);
  text-align: center;
}}
@media (max-width: 900px) {{
  .grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>
</head>
<body>
<nav class="nav">
  <div class="container nav-inner">
    <div class="brand">{brand}</div>
    <div class="links">{nav_html}</div>
  </div>
</nav>

<header class="hero">
  <div class="container">
    <div class="hero-card">
      <div class="eyebrow">Optimised website concept</div>
      <h1>{title}</h1>
      <p>This is a functional mock webpage that shows a clearer, more structured and more recommendation-ready version of the page.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="#main">Explore page</a>
        <a class="btn btn-secondary" href="#">Contact team</a>
      </div>
    </div>
  </div>
</header>

<main id="main" class="container grid">
  <section class="panel">
    {''.join(parsed)}
  </section>

  <aside>
    <div class="panel side-card">
      <h3>Why this version is stronger</h3>
      <p>Clearer structure, better scannability, stronger sectioning, and a more believable page hierarchy.</p>
    </div>
    <div class="panel side-card badge-card">
      <div class="badge">AI-readable structure</div>
      <div class="badge">Human-friendly page flow</div>
      <div class="badge">Implementation-ready concept</div>
    </div>
  </aside>
</main>

<footer class="footer">
  <div class="container">Client-facing mock webpage preview</div>
</footer>
</body>
</html>"""


# ============================================================
# FETCH ORIGINAL PAGE CLUES
# ============================================================
with st.spinner("Reading original page structure..."):
    original = page_snapshot(geo["url"])

brand_name = company.get("name", "") or "Brand"
st.subheader("🏢 Company Context")
st.write(f"**Company:** {brand_name}")
st.write(f"**Industry:** {company.get('industry', '')}")
st.write(f"**Niche:** {company.get('niche', '')}")

st.subheader("🎯 Original Page Clues")
st.write(f"**Original title:** {original['title']}")
if original["nav_items"]:
    st.write(f"**Detected nav items:** {', '.join(original['nav_items'])}")
if original["headings"]:
    st.write(f"**Detected headings:** {', '.join(original['headings'][:8])}")

generate = st.button("Generate / Refresh Real Mock Website", type="primary", use_container_width=True)

# ============================================================
# PROMPT FOR BETTER MOCKUP
# ============================================================
SYSTEM_PROMPT = """
You are a senior conversion-focused web designer.

Your job is to produce a complete, realistic HTML website prototype.

CRITICAL REQUIREMENTS:
- Output ONLY raw HTML
- Start with <!DOCTYPE html> and end with </html>
- No markdown
- No explanation
- No JavaScript
- No external images
- No external fonts
- Use CSS only
- Use system fonts only
- The result must look like a real premium website, not a text dump
- Preserve some resemblance to the original site using:
  - title
  - nav labels
  - section/headline patterns
  - colour clues if provided
- Build:
  - sticky navigation
  - strong hero section
  - section hierarchy
  - cards / content panels
  - side panels or feature blocks where useful
  - multiple CTAs
  - believable footer
- Make it fully responsive
- Turn the rewritten content into a client-facing website concept
- Show [DATA NEEDED: ...] placeholders as visually distinct dashed boxes
- Prioritise strong human UX and clarity, not only AI structure
"""

# ============================================================
# GENERATE
# ============================================================
if generate or not geo.get("mock_html"):
    user_prompt = f"""
COMPANY:
Name: {brand_name}
Industry: {company.get("industry", "")}
Niche: {company.get("niche", "")}

ORIGINAL PAGE TITLE:
{original["title"]}

ORIGINAL META DESCRIPTION:
{original["meta_description"]}

ORIGINAL NAV ITEMS:
{original["nav_items"]}

ORIGINAL HEADINGS:
{original["headings"][:12]}

COLOUR CLUES:
{original["colours"]}

REWRITTEN CONTENT:
{rewritten_content}

GOAL:
Build a real, scrollable, realistic HTML website prototype that feels like a strong, structured version of the original site — not just a page of text.
"""

    try:
        with st.spinner("Building better mock website..."):
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    top_p=0.1,
                    top_k=1,
                    candidate_count=1,
                    max_output_tokens=8192,
                    seed=42,
                    system_instruction=SYSTEM_PROMPT
                )
            )

        html_raw = clean_html_output(response.text)

        if not html_looks_valid(html_raw):
            html_raw = fallback_html(
                title=original["title"] or page_title_value,
                brand=brand_name,
                nav_items=original["nav_items"],
                content=rewritten_content
            )

        geo["mock_html"] = html_raw
        st.session_state.geo_context = geo
        st.success("✅ Real mock website generated.")

    except Exception as e:
        st.error(f"Mock website generation failed: {str(e)}")

# ============================================================
# DISPLAY
# ============================================================
mock_html = geo.get("mock_html", "")

if mock_html:
    st.subheader("🌐 Live Scrollable Website Preview")
    components.html(mock_html, height=1700, scrolling=True)

    st.subheader("👨‍💻 HTML Code")
    st.caption("Copy the full HTML below or download it as a file.")
    st.text_area("HTML Output", mock_html, height=420)

    st.download_button(
        "⬇️ Download HTML File",
        mock_html,
        "geo_mock_website.html",
        "text/html",
        use_container_width=True
    )
