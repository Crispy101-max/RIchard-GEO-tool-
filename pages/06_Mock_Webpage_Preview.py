import os
import re
import streamlit as st
import streamlit.components.v1 as components
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
    "Generate a **real scrollable webpage mockup** from the rewritten GEO content. "
    "You can preview it, copy the HTML, and download it for client presentation."
)

# ============================================================
# GEO CONTEXT GUARD
# ============================================================
if "geo_context" not in st.session_state or "url" not in st.session_state.geo_context:
    st.warning("Please start a GEO job from the Home page first.")
    st.stop()

geo = st.session_state.geo_context

rewritten_content = geo.get("rewritten_content", "")
company = geo.get("company", {})
page_snapshot = geo.get("page_snapshot", {})

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
def clean_html_output(html_raw):
    html_raw = html_raw.strip()

    if html_raw.startswith("```"):
        html_raw = re.sub(r"^```(?:html)?\s*", "", html_raw)
        html_raw = re.sub(r"\s*```$", "", html_raw)

    return html_raw.strip()


def html_looks_valid(html_raw):
    lowered = html_raw.strip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html")


def replace_data_needed_boxes(text):
    pattern = r"\[DATA NEEDED:(.*?)\]"

    def repl(match):
        content = match.group(1).strip()
        return (
            '<div class="data-needed">'
            "<strong>DATA NEEDED</strong><br>"
            f"{content}"
            "</div>"
        )

    return re.sub(pattern, repl, text)


def markdownish_to_basic_html(text):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = replace_data_needed_boxes(safe)

    lines = safe.split("\n")
    html_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            html_parts.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            html_parts.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("- "):
            html_parts.append(f"<li>{stripped[2:]}</li>")
        else:
            html_parts.append(f"<p>{stripped}</p>")

    final_parts = []
    in_list = False

    for part in html_parts:
        if part.startswith("<li>"):
            if not in_list:
                final_parts.append("<ul>")
                in_list = True
            final_parts.append(part)
        else:
            if in_list:
                final_parts.append("</ul>")
                in_list = False
            final_parts.append(part)

    if in_list:
        final_parts.append("</ul>")

    return "\n".join(final_parts)


def build_fallback_html(title, brand_name, content_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --accent: #6366f1;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.08);
      --shadow: 0 20px 60px rgba(0,0,0,0.28);
      --radius: 20px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: linear-gradient(180deg, var(--bg), #111827);
      color: var(--text);
      line-height: 1.6;
    }}
    .container {{
      width: min(1100px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .nav {{
      position: sticky;
      top: 0;
      backdrop-filter: blur(10px);
      background: rgba(15, 23, 42, 0.82);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      z-index: 20;
    }}
    .nav-inner {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 0;
    }}
    .brand {{
      font-weight: 700;
      font-size: 1.1rem;
      color: white;
    }}
    .nav-links {{
      display: flex;
      gap: 16px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .hero {{
      padding: 72px 0 36px;
    }}
    .hero-card {{
      background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 28px;
      box-shadow: var(--shadow);
      padding: 42px;
    }}
    .eyebrow {{
      display: inline-block;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(99, 102, 241, 0.18);
      color: #c7d2fe;
      font-size: 0.85rem;
      margin-bottom: 14px;
    }}
    .hero h1 {{
      font-size: clamp(2rem, 5vw, 3.6rem);
      line-height: 1.05;
      margin: 0 0 16px;
      color: white;
    }}
    .hero p {{
      font-size: 1.05rem;
      color: var(--muted);
      max-width: 760px;
      margin: 0 0 24px;
    }}
    .cta {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 14px 22px;
      border-radius: 14px;
      background: var(--accent);
      color: white;
      text-decoration: none;
      font-weight: 600;
      box-shadow: 0 10px 30px rgba(99, 102, 241, 0.35);
    }}
    .section {{
      padding: 20px 0 32px;
    }}
    .content-card {{
      background: var(--surface);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: var(--radius);
      padding: 32px;
      box-shadow: var(--shadow);
    }}
    h2 {{
      color: white;
      margin-top: 26px;
      margin-bottom: 12px;
      font-size: 1.7rem;
    }}
    h3 {{
      color: white;
      margin-top: 20px;
      margin-bottom: 8px;
      font-size: 1.2rem;
    }}
    p {{
      margin: 0 0 14px;
      color: var(--text);
    }}
    ul {{
      padding-left: 22px;
      margin-top: 8px;
      margin-bottom: 16px;
    }}
    li {{
      margin-bottom: 8px;
    }}
    .data-needed {{
      border: 2px dashed var(--danger);
      background: var(--danger-bg);
      color: #fecaca;
      padding: 16px;
      border-radius: 14px;
      margin: 16px 0;
    }}
    .footer {{
      padding: 32px 0 56px;
      color: var(--muted);
      text-align: center;
      font-size: 0.95rem;
    }}
    @media (max-width: 768px) {{
      .hero-card,
      .content-card {{
        padding: 24px;
      }}
      .nav-links {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="container nav-inner">
      <div class="brand">{brand_name}</div>
      <div class="nav-links">
        <span>Overview</span>
        <span>Benefits</span>
        <span>FAQs</span>
        <span>Contact</span>
      </div>
    </div>
  </nav>

  <header class="hero">
    <div class="container">
      <div class="hero-card">
        <div class="eyebrow">Optimised GEO website concept</div>
        <h1>{title}</h1>
        <p>This is a functional mock webpage generated from your rewritten GEO content. It is intended to give the client a realistic flavour of what an optimised page structure looks like.</p>
        <a class="cta" href="#content">View Page</a>
      </div>
    </div>
  </header>

  <main class="section" id="content">
    <div class="container">
      <div class="content-card">
        {content_html}
      </div>
    </div>
  </main>

  <footer class="footer">
    <div class="container">
      GEO mock webpage for {brand_name}
    </div>
  </footer>
</body>
</html>"""


# ============================================================
# DISPLAY CONTEXT
# ============================================================
st.subheader("🏢 Company Context")
st.write(f"**Company:** {company.get('name', '')}")
st.write(f"**Industry:** {company.get('industry', '')}")
st.write(f"**Niche:** {company.get('niche', '')}")

st.subheader("🎯 Source")
st.write(f"**Page title:** {page_title}")

generate = st.button("Generate / Refresh Mock Website", type="primary", use_container_width=True)

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a professional web designer.

Your ONLY job is to produce a complete, polished HTML webpage mockup.

IMPORTANT:
- Output ONLY raw HTML
- Start with <!DOCTYPE html> and end with </html>
- No markdown
- No explanation
- No JavaScript
- No external images
- No external fonts
- Use CSS only
- Use system fonts only
- Build a realistic, premium, scrollable webpage
- Include:
  - sticky navigation bar
  - hero section
  - multiple content sections
  - cards / panels where appropriate
  - CTA button
  - footer
- Make it fully responsive
- Preserve the rewritten content structure
- Show every [DATA NEEDED: ...] item as a clearly styled red dashed placeholder box
- Return the SINGLE BEST page layout
"""

# ============================================================
# RUN HTML GENERATION
# ============================================================
if generate or not geo.get("mock_html"):
    user_prompt = f"""
BRAND NAME:
{company.get("name", "")}

INDUSTRY:
{company.get("industry", "")}

NICHE:
{company.get("niche", "")}

PAGE TITLE:
{page_title}

REWRITTEN CONTENT:
{rewritten_content}

GOAL:
Render this into a real, scrollable, realistic HTML website mockup that a client can review.
"""

    try:
        with st.spinner("Building mock website..."):
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
            fallback_content = markdownish_to_basic_html(rewritten_content)
            html_raw = build_fallback_html(page_title, company.get("name", "Brand"), fallback_content)

        geo["mock_html"] = html_raw
        st.session_state.geo_context = geo

        st.success("✅ Mock website generated and saved to GEO workflow context.")

    except Exception as e:
        st.error(f"Mock website generation failed: {str(e)}")

# ============================================================
# DISPLAY OUTPUT
# ============================================================
mock_html = geo.get("mock_html", "")

if mock_html:
    st.subheader("🌐 Live Scrollable Website Preview")
    components.html(mock_html, height=1600, scrolling=True)

    st.subheader("👨‍💻 HTML Code")
    st.caption("Use the box below to copy the full HTML easily and send it to clients or developers.")
    st.text_area("HTML Output", mock_html, height=420)

    st.download_button(
        "⬇️ Download HTML File",
        mock_html,
        "geo_mock_website.html",
        "text/html",
        use_container_width=True
    )
