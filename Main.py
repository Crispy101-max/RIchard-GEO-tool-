import os
import json
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from google import genai

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Content Auditor",
    page_icon="🚀",
    layout="wide"
)

# ============================================================
# CONSTANTS
# ============================================================
HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")

DEFAULT_PALETTE = {
    "background": "#0f172a",
    "surface": "#1e293b",
    "accent": "#6366f1",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
}

# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key() -> str:
    """
    Loads API key in this order:
    1) Streamlit secrets: st.secrets["API_Key"]
    2) Environment variable: API_Key
    3) Environment variable: GEMINI_API_KEY
    """
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass

    if os.getenv("API_Key"):
        return os.getenv("API_Key", "")

    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY", "")

    return ""


API_KEY = get_api_key()

if not API_KEY:
    st.error(
        "No Gemini API key found.\n\n"
        "Please add it in one of these ways:\n"
        "1. Streamlit secrets as `API_Key`\n"
        "2. Environment variable `API_Key`\n"
        "3. Environment variable `GEMINI_API_KEY`"
    )
    st.stop()

client = genai.Client(api_key=API_KEY)

# ============================================================
# HELPERS
# ============================================================
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def domain_to_brand(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.replace("www.", "")
        brand = netloc.split(".")[0]
        return brand.replace("-", " ").replace("_", " ").title()
    except Exception:
        return "Brand"


def extract_hex_colours(css_text: str, inline_styles: List[str]) -> List[str]:
    combined = (css_text or "") + "\n" + "\n".join(inline_styles or [])
    colours = HEX_PATTERN.findall(combined)

    seen = set()
    cleaned = []

    for c in colours:
        c = c.lower()

        # Expand shorthand hex: #abc -> #aabbcc
        if len(c) == 4:
            c = "#" + "".join(ch * 2 for ch in c[1:])

        if c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned[:10]


def infer_palette(colours: List[str]) -> Dict[str, str]:
    palette = DEFAULT_PALETTE.copy()

    if len(colours) >= 1:
        palette["accent"] = colours[0]
    if len(colours) >= 2:
        palette["background"] = colours[1]
    if len(colours) >= 3:
        palette["surface"] = colours[2]
    if len(colours) >= 4:
        palette["text"] = colours[3]
    if len(colours) >= 5:
        palette["muted"] = colours[4]

    return palette


def extract_website_data(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else domain_to_brand(url)

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    # Save CSS / inline styles before removing elements
    style_tags = soup.find_all("style")
    css_text = "\n".join([s.get_text(" ", strip=True) for s in style_tags])

    inline_styles = []
    for tag in soup.find_all(style=True):
        style_val = tag.get("style", "")
        if "color" in style_val.lower() or "background" in style_val.lower():
            inline_styles.append(style_val)

    colours = extract_hex_colours(css_text, inline_styles)

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        txt = clean_whitespace(h.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    # Remove obvious non-content elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))
    page_text = page_text[:25000]  # avoid excessive token usage

    return {
        "url": url,
        "title": title,
        "brand_name": domain_to_brand(url),
        "meta_description": meta_description,
        "headings": headings[:20],
        "page_text": page_text,
        "raw_css_excerpt": css_text[:4000],
        "inline_styles_excerpt": inline_styles[:20],
        "colours": colours,
        "palette": infer_palette(colours),
    }


def parse_json_from_model(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    # Remove code fences if model returns markdown
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start:end + 1]
        return json.loads(snippet)

    raise ValueError("Could not parse valid JSON from model response.")


def clean_html_output(html_raw: str) -> str:
    html_raw = html_raw.strip()

    if html_raw.startswith("```"):
        html_raw = re.sub(r"^```(?:html)?\s*", "", html_raw)
        html_raw = re.sub(r"\s*```$", "", html_raw)

    return html_raw.strip()


def html_looks_valid(html_raw: str) -> bool:
    lowered = html_raw.strip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html")


def replace_data_needed_boxes(text: str) -> str:
    """
    Turns [DATA NEEDED: ...] into styled HTML boxes for fallback rendering.
    """
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


def markdownish_to_basic_html(text: str) -> str:
    """
    Very lightweight converter for fallback rendering if model fails to return HTML.
    """
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


def build_fallback_html(
    brand_name: str,
    title: str,
    rewritten_content: str,
    palette: Dict[str, str],
) -> str:
    content_html = markdownish_to_basic_html(rewritten_content)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} - GEO Mockup</title>
  <style>
    :root {{
      --bg: {palette["background"]};
      --surface: {palette["surface"]};
      --accent: {palette["accent"]};
      --text: {palette["text"]};
      --muted: {palette["muted"]};
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.08);
      --shadow: 0 20px 60px rgba(0,0,0,0.25);
      --radius: 20px;
    }}

    * {{
      box-sizing: border-box;
    }}

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
      background: rgba(15, 23, 42, 0.75);
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
      letter-spacing: 0.2px;
    }}

    .hero {{
      padding: 72px 0 32px;
    }}

    .hero-card {{
      background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
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
    }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="container nav-inner">
      <div class="brand">{brand_name}</div>
      <div style="color: var(--muted); font-size: 0.95rem;">GEO Website Mockup</div>
    </div>
  </nav>

  <header class="hero">
    <div class="container">
      <div class="hero-card">
        <div class="eyebrow">Visualised from your original site</div>
        <h1>{title}</h1>
        <p>This is a fallback visual mockup generated because the AI did not return fully valid HTML. Your rewritten GEO content is still visualised below.</p>
        <a class="cta" href="#content">View Rewritten Content</a>
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
      GEO mock webpage visualisation for {brand_name}
    </div>
  </footer>
</body>
</html>"""


def add_usage_to_session(response: Any):
    try:
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0

        st.session_state.total_input_tokens += prompt_tokens
        st.session_state.total_output_tokens += output_tokens

        # Using your original pricing assumptions
        st.session_state.total_cost += (
            (prompt_tokens / 1_000_000) * 1.25
            + (output_tokens / 1_000_000) * 10.00
        )
    except Exception:
        pass


def call_gemini(user_text: str, system_instruction: str):
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        config={"system_instruction": system_instruction},
        contents=[{"role": "user", "parts": [{"text": user_text}]}],
    )
    return response


# ============================================================
# SESSION STATE
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "scores" not in st.session_state:
    st.session_state.scores = {
        "AI_Readability": "0",
        "Fact_Density": "0",
        "Authority": "0",
    }

if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0

if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("📊 GEO Scoreboard")
    st.metric("AI Readability", f"{st.session_state.scores['AI_Readability']}/100")
    st.metric("Fact Density", f"{st.session_state.scores['Fact_Density']}%")
    st.metric("Entity Authority", f"{st.session_state.scores['Authority']}/100")

    st.divider()

    st.subheader("🔢 Token Usage")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Input", f"{st.session_state.total_input_tokens:,}")
    with c2:
        st.metric("Output", f"{st.session_state.total_output_tokens:,}")

    st.metric("💰 Session Cost", f"${st.session_state.total_cost:.4f}")
    st.caption("Gemini 2.5 Pro: $1.25/1M input · $10.00/1M output")

    st.divider()

    if st.button("Clear History"):
        st.session_state.messages = []
        st.session_state.scores = {
            "AI_Readability": "0",
            "Fact_Density": "0",
            "Authority": "0",
        }
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost = 0.0
        st.rerun()

# ============================================================
# MAIN UI
# ============================================================
st.title("🚀 GEO Content Auditor")
st.write(
    "Paste a **URL** or **text** to audit GEO optimisation, rewrite it for AI search, "
    "and generate a **visual mock webpage** based on the original site's theme."
)

# ============================================================
# RENDER PREVIOUS CHAT + VISUAL MOCKUPS
# ============================================================
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            audit_tab, preview_tab, raw_tab = st.tabs(
                ["📋 Audit", "🌐 Mock Webpage Preview", "👨‍💻 Raw HTML"]
            )

            with audit_tab:
                st.markdown(msg["content"])

            with preview_tab:
                if msg.get("html"):
                    st.subheader("Live GEO Mockup")
                    st.caption(
                        "This is a visual mock webpage based on the rewritten GEO content and the original website theme."
                    )
                    components.html(msg["html"], height=1500, scrolling=True)

                    st.download_button(
                        label="⬇️ Download HTML File",
                        data=msg["html"],
                        file_name="geo_optimised_page.html",
                        mime="text/html",
                        use_container_width=True,
                        key=f"download_{idx}",
                    )
                else:
                    st.warning("No visual webpage mockup was generated for this result.")

            with raw_tab:
                if msg.get("html"):
                    st.code(msg["html"], language="html")
                else:
                    st.info("No HTML available.")

# ============================================================
# LATEST MOCKUP SECTION
# ============================================================
latest_mockup = None
for m in reversed(st.session_state.messages):
    if m.get("role") == "assistant" and m.get("html"):
        latest_mockup = m
        break

if latest_mockup:
    st.divider()
    st.header("🌐 Latest GEO Website Mockup")
    st.caption(
        "This is the latest generated webpage mockup. Scroll inside the preview to see the full page."
    )
    components.html(latest_mockup["html"], height=1600, scrolling=True)

# ============================================================
# CHAT INPUT
# ============================================================
if prompt := st.chat_input("Enter URL (starting with http) or paste website content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    source_mode = "text"
    source_data = None

    # --------------------------------------------------------
    # STEP 0: READ INPUT
    # --------------------------------------------------------
    if prompt.strip().startswith("http"):
        source_mode = "url"
        with st.status("🔍 Reading website..."):
            try:
                source_data = extract_website_data(prompt)

                if not source_data["page_text"]:
                    st.error("The page was fetched, but no readable text content was found.")
                    st.stop()

                if len(source_data["page_text"]) < 300:
                    st.warning(
                        "This page has very little readable text. It may be heavily JavaScript-rendered, "
                        "so the extracted content could be incomplete."
                    )

            except Exception as e:
                st.error(f"Error scraping webpage: {str(e)}")
                st.stop()
    else:
        source_data = {
            "url": "",
            "title": "Pasted Content",
            "brand_name": "Brand",
            "meta_description": "",
            "headings": [],
            "page_text": clean_whitespace(prompt)[:25000],
            "raw_css_excerpt": "",
            "inline_styles_excerpt": [],
            "colours": [],
            "palette": DEFAULT_PALETTE.copy(),
        }

    try:
        # --------------------------------------------------------
        # STEP 1: ANALYSE + REWRITE CONTENT
        # --------------------------------------------------------
        ANALYSIS_SYSTEM = """
You are a senior Generative Engine Optimisation (GEO) strategist.

Your task:
1. Assess what prevents the page from being GEO-optimised.
2. Rewrite the page so it is GEO-optimised.
3. Keep the content and meaning roughly the same.
4. Improve structure, headings, chunking, clarity, answer-first delivery, entity definitions, and trust signals.
5. NEVER invent facts, statistics, credentials, case studies, outcomes, names, or results.
6. If information is missing, insert placeholders exactly in this format:
   [DATA NEEDED: short description]

IMPORTANT RULES:
- Only use facts already present in the source content.
- If the source page is thin, create a stronger structure using the existing meaning.
- Keep it commercially realistic and useful.
- Prefer natural-language question headings where suitable.
- Return VALID JSON only.
- Do not output commentary outside JSON.

Return JSON only in exactly this structure:
{
  "changes_made": ["...", "..."],
  "rewritten_content": "...",
  "data_gaps": ["...", "..."],
  "scores": {
    "readability": 0,
    "fact_density": 0,
    "authority": 0
  }
}
"""

        ANALYSIS_USER = f"""
SOURCE TYPE: {source_mode}

PAGE TITLE:
{source_data["title"]}

BRAND NAME:
{source_data["brand_name"]}

META DESCRIPTION:
{source_data["meta_description"]}

ORIGINAL HEADINGS:
{json.dumps(source_data["headings"], ensure_ascii=False)}

SOURCE CONTENT:
{source_data["page_text"]}

Rewrite requirements:
- Keep the original meaning and offer roughly the same.
- Make the structure much more GEO-friendly.
- Start sections with the key answer / main point.
- Define important terms on first mention.
- Break long paragraphs into short chunks.
- Remove vague filler.
- Add [DATA NEEDED: ...] where specifics are missing.
- Make the page easier for AI systems to interpret and cite.
"""

        with st.status("🧠 Step 1/2 — Auditing and rewriting content..."):
            analysis_response = call_gemini(ANALYSIS_USER, ANALYSIS_SYSTEM)
            add_usage_to_session(analysis_response)
            analysis_json = parse_json_from_model(analysis_response.text)

        changes_made = analysis_json.get("changes_made", [])
        rewritten_content = analysis_json.get("rewritten_content", "").strip()
        data_gaps = analysis_json.get("data_gaps", [])
        scores = analysis_json.get("scores", {})

        if not rewritten_content:
            st.error("The AI did not return rewritten content.")
            st.stop()

        st.session_state.scores["AI_Readability"] = str(scores.get("readability", 0))
        st.session_state.scores["Fact_Density"] = str(scores.get("fact_density", 0))
        st.session_state.scores["Authority"] = str(scores.get("authority", 0))

        display_text = "## 1. CHANGES MADE\n"
        if changes_made:
            for item in changes_made[:5]:
                display_text += f"- {item}\n"
        else:
            display_text += "- No specific changes returned.\n"

        display_text += "\n## 2. GEO-REWRITTEN CONTENT\n"
        display_text += rewritten_content + "\n"

        display_text += "\n## 3. DATA GAPS LIST\n"
        if data_gaps:
            for gap in data_gaps:
                display_text += f"- {gap}\n"
        else:
            display_text += "- No major gaps identified.\n"

        # --------------------------------------------------------
        # STEP 2: GENERATE VISUAL HTML MOCKUP
        # --------------------------------------------------------
        palette = source_data["palette"]

        HTML_SYSTEM = """
You are a professional web designer.

Your ONLY job is to produce a complete, visually polished HTML webpage mockup.

IMPORTANT:
- This is a VISUAL WEBSITE MOCKUP.
- The user must be able to PHYSICALLY SEE the redesigned webpage in an embedded HTML preview.
- Output ONLY raw HTML.
- Start with <!DOCTYPE html> and end with </html>.
- No markdown.
- No explanation.
- No JavaScript.
- No external image URLs.
- No external fonts.
- Use CSS only.
- Use system fonts only.
- The mockup should feel realistic and premium, not like a wireframe.
"""

        HTML_USER = f"""
Create a fully responsive, professional HTML webpage mockup using the GEO-rewritten content below.

GOAL:
- This is a visual mockup of the improved webpage.
- It should preserve the original brand feel where possible.
- It should use the original site's theme clues and colours.
- It should visually show the improved GEO structure.
- It is for presentation / visualisation, not for production deployment.

BRAND NAME:
{source_data["brand_name"]}

PAGE TITLE:
{source_data["title"]}

ORIGINAL URL:
{source_data["url"]}

ORIGINAL HEADINGS:
{json.dumps(source_data["headings"], ensure_ascii=False)}

THEME COLOURS TO USE:
{json.dumps(palette)}

RAW HEX COLOURS FOUND:
{json.dumps(source_data["colours"], ensure_ascii=False)}

CSS EXCERPT FOR STYLE CLUES:
{source_data["raw_css_excerpt"]}

INLINE STYLE CLUES:
{json.dumps(source_data["inline_styles_excerpt"], ensure_ascii=False)}

GEO-REWRITTEN CONTENT:
{rewritten_content}

HTML REQUIREMENTS:
- Complete HTML document from <!DOCTYPE html> to </html>
- Use the colour palette exactly where possible
- Include a top navigation bar
- Include a hero section
- Include all main sections from the rewritten content
- Preserve the rewritten section order
- Use good spacing, visual hierarchy, cards, and subtle shadows
- Use a CTA button
- Include a footer
- Make it fully responsive
- Show every [DATA NEEDED: ...] item as a clearly styled red dashed placeholder box
- Use gradients, surfaces, panels, and layout to make it look like a real website
- No lorem ipsum
- No fake testimonials
- No fake results
- No fake case study numbers
- No JavaScript
- Output raw HTML only
"""

        with st.status("🎨 Step 2/2 — Building visual mock webpage..."):
            html_response = call_gemini(HTML_USER, HTML_SYSTEM)
            add_usage_to_session(html_response)
            html_raw = clean_html_output(html_response.text)

        # Build fallback page if model returns bad HTML
        if not html_looks_valid(html_raw):
            html_raw = build_fallback_html(
                brand_name=source_data["brand_name"],
                title=source_data["title"],
                rewritten_content=rewritten_content,
                palette=palette,
            )

        assistant_message = {
            "role": "assistant",
            "content": display_text,
            "html": html_raw,
            "audit": {
                "changes_made": changes_made,
                "data_gaps": data_gaps,
                "scores": scores,
            },
        }

        st.session_state.messages.append(assistant_message)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {str(e)}")
