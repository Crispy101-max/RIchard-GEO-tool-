import streamlit as st
import streamlit.components.v1 as components
from google import genai
import re
import requests
from bs4 import BeautifulSoup

client = genai.Client(api_key=st.secrets["API_Key"])

# ── URL Scraper ───────────────────────────────────────────────
def extract_website_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        style_tags = soup.find_all('style')
        css_text = "\n".join([s.get_text() for s in style_tags])
        color_hints = []
        for tag in soup.find_all(style=True):
            style_val = tag.get('style', '')
            if 'color' in style_val or 'background' in style_val:
                color_hints.append(style_val)

        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        page_text = soup.get_text(separator=' ', strip=True)
        colour_context = f"\n\n---COLOUR CONTEXT---\n{css_text[:3000]}\nInline colour hints: {'; '.join(color_hints[:20])}"
        return page_text + colour_context

    except Exception as e:
        return f"Error scraping {url}: {str(e)}"


# ── HTML Builder — Python builds the page, not Gemini ────────
def build_html_page(sections: dict, colours: dict) -> str:
    bg      = colours.get("bg",      "#0f172a")
    card    = colours.get("card",    "#1e293b")
    accent  = colours.get("accent",  "#6366f1")
    text    = colours.get("text",    "#e2e8f0")
    muted   = colours.get("muted",   "#94a3b8")
    border  = colours.get("border",  "#334155")
    brand   = sections.get("brand",  "Your Brand")

    def render_section(heading, body, bg_override=None):
        section_bg = bg_override if bg_override else card
        # Style [DATA NEEDED] items in red dashed boxes
        body_html = body.replace(
            "[DATA NEEDED",
            '<span class="data-needed">[DATA NEEDED'
        ).replace(
            "]", "]</span>", 1
        ) if "[DATA NEEDED" in body else body

        # Convert newlines to paragraph breaks
        paragraphs = [f"<p>{p.strip()}</p>" for p in body.split("\n") if p.strip()]
        body_rendered = "\n".join(paragraphs)

        return f"""
        <section style="background:{section_bg}; padding:70px 20px; border-bottom:1px solid {border};">
            <div style="max-width:960px; margin:0 auto;">
                <h2 style="color:{text}; font-size:2rem; margin-bottom:24px; line-height:1.3;">{heading}</h2>
                <div style="color:{muted}; font-size:1.05rem; line-height:1.8;">{body_rendered}</div>
            </div>
        </section>"""

    def render_cards(heading, items: list, bg_override=None):
        section_bg = bg_override if bg_override else bg
        cards_html = ""
        for item in items:
            title = item.get("title", "")
            body  = item.get("body",  "")
            cards_html += f"""
            <div style="background:{card}; border:1px solid {border}; border-radius:12px;
                        padding:28px; box-shadow:0 4px 20px rgba(0,0,0,0.3);">
                <h3 style="color:{text}; font-size:1.2rem; margin-bottom:12px;">{title}</h3>
                <p style="color:{muted}; font-size:1rem; line-height:1.7;">{body}</p>
            </div>"""

        return f"""
        <section style="background:{section_bg}; padding:70px 20px; border-bottom:1px solid {border};">
            <div style="max-width:960px; margin:0 auto;">
                <h2 style="color:{text}; font-size:2rem; margin-bottom:40px; text-align:center;">{heading}</h2>
                <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:24px;">
                    {cards_html}
                </div>
            </div>
        </section>"""

    # Build all sections
    hero_title   = sections.get("hero_title",   "Your GEO-Optimised Headline")
    hero_sub     = sections.get("hero_sub",     "Your updated subheading goes here.")
    hero_cta     = sections.get("hero_cta",     "Get Your Free GEO Audit")
    what_heading = sections.get("what_heading", "What Is This Service?")
    what_body    = sections.get("what_body",    "")
    how_heading  = sections.get("how_heading",  "How Does It Work?")
    how_body     = sections.get("how_body",     "")
    results_heading = sections.get("results_heading", "What Results Can You Expect?")
    results_items   = sections.get("results_items",   [])
    about_heading   = sections.get("about_heading",   "Who Are We?")
    about_body      = sections.get("about_body",      "")
    data_gaps       = sections.get("data_gaps",       [])

    data_gaps_html = "".join([
        f'<li style="margin-bottom:8px; color:{muted};">'
        f'<span style="color:#f87171; font-weight:600;">●</span> {g}</li>'
        for g in data_gaps
    ])

    results_section = render_cards(results_heading, results_items) if results_items else \
        render_section(results_heading, sections.get("results_body", "[DATA NEEDED: Add client results or case studies]"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand} — GEO Optimised</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
        background:{bg}; color:{text}; line-height:1.6; }}
.data-needed {{
    display:inline-block; background:rgba(239,68,68,0.1);
    border:2px dashed #ef4444; border-radius:6px;
    padding:2px 8px; color:#fca5a5; font-style:italic; font-size:0.9em;
}}
a {{ color:{accent}; }}
@media(max-width:768px) {{
    h1 {{ font-size:2rem !important; }}
    h2 {{ font-size:1.5rem !important; }}
}}
</style>
</head>
<body>

<!-- NAV -->
<nav style="background:{card}; border-bottom:1px solid {border};
            padding:16px 20px; position:sticky; top:0; z-index:100;">
    <div style="max-width:960px; margin:0 auto; display:flex;
                justify-content:space-between; align-items:center;">
        <span style="font-size:1.3rem; font-weight:700; color:{text};">{brand}</span>
        <a href="#contact" style="background:{accent}; color:#fff; padding:10px 22px;
           border-radius:8px; text-decoration:none; font-weight:600; font-size:0.95rem;">
           {hero_cta}
        </a>
    </div>
</nav>

<!-- HERO -->
<header style="background: linear-gradient(135deg, {bg} 0%, {card} 100%);
               padding:100px 20px; text-align:center; border-bottom:1px solid {border};">
    <div style="max-width:800px; margin:0 auto;">
        <h1 style="font-size:3.2rem; font-weight:800; color:{text};
                   line-height:1.15; margin-bottom:20px; letter-spacing:-1px;">
            {hero_title}
        </h1>
        <p style="font-size:1.2rem; color:{muted}; max-width:600px;
                  margin:0 auto 36px auto; line-height:1.7;">
            {hero_sub}
        </p>
        <a href="#contact" style="background:{accent}; color:#fff; padding:16px 36px;
           border-radius:10px; text-decoration:none; font-weight:700;
           font-size:1.1rem; display:inline-block;">
            {hero_cta}
        </a>
    </div>
</header>

{render_section(what_heading, what_body, bg)}
{render_section(how_heading,  how_body,  card)}
{results_section}
{render_section(about_heading, about_body, card)}

<!-- DATA GAPS PANEL -->
<section style="background:#1a0a0a; padding:60px 20px;
                border-top:2px dashed #ef4444; border-bottom:1px solid {border};">
    <div style="max-width:960px; margin:0 auto;">
        <h2 style="color:#f87171; font-size:1.5rem; margin-bottom:8px;">
            📋 Client To-Do List — Content Needed to Complete This Page
        </h2>
        <p style="color:{muted}; margin-bottom:24px; font-size:0.95rem;">
            The following information is missing from your current site.
            Providing it will significantly improve your GEO score and AI visibility.
        </p>
        <ul style="list-style:none; padding:0;">
            {data_gaps_html}
        </ul>
    </div>
</section>

<!-- CTA / CONTACT -->
<section id="contact" style="background:{bg}; padding:80px 20px; text-align:center;">
    <div style="max-width:700px; margin:0 auto;">
        <h2 style="color:{text}; font-size:2rem; margin-bottom:16px;">
            Ready to Dominate AI Search?
        </h2>
        <p style="color:{muted}; font-size:1.1rem; margin-bottom:32px;">
            Get in touch to see how GEO can make your brand the answer AI gives your customers.
        </p>
        <a href="#" style="background:{accent}; color:#fff; padding:16px 40px;
           border-radius:10px; text-decoration:none; font-weight:700; font-size:1.1rem;">
            {hero_cta}
        </a>
    </div>
</section>

<!-- FOOTER -->
<footer style="background:{card}; padding:30px 20px; text-align:center;
               border-top:1px solid {border};">
    <p style="color:{muted}; font-size:0.9rem;">
        © 2025 {brand}. GEO-optimised with Janus Labs.
    </p>
</footer>

</body>
</html>"""


# ── Colour extractor ──────────────────────────────────────────
def extract_colours(css_text: str) -> dict:
    defaults = {"bg":"#0f172a","card":"#1e293b","accent":"#6366f1",
                "text":"#e2e8f0","muted":"#94a3b8","border":"#334155"}
    hex_pattern = r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})'
    found = re.findall(hex_pattern, css_text)
    if len(found) >= 3:
        colours = ["#" + c for c in found]
        # Heuristic: darkest = bg, mid = card, most vivid = accent
        def brightness(h):
            h = h.lstrip("#")
            if len(h) == 3: h = h[0]*2 + h[1]*2 + h[2]*2
            r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return 0.299*r + 0.587*g + 0.114*b
        sorted_c = sorted(set(colours), key=brightness)
        if len(sorted_c) >= 2:
            defaults["bg"]   = sorted_c[0]
            defaults["card"] = sorted_c[1] if len(sorted_c) > 1 else defaults["card"]
        for c in colours:
            h = c.lstrip("#")
            if len(h) == 3: h = h[0]*2+h[1]*2+h[2]*2
            r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
            saturation = max(r,g,b) - min(r,g,b)
            if saturation > 80:
                defaults["accent"] = c
                break
    return defaults


# ── Session State ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scores" not in st.session_state:
    st.session_state.scores = {"AI_Readability":"0","Fact_Density":"0","Authority":"0"}
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 GEO Scoreboard")
    st.metric("AI Readability", f"{st.session_state.scores['AI_Readability']}/100")
    st.metric("Fact Density",   f"{st.session_state.scores['Fact_Density']}%")
    st.metric("Entity Authority",f"{st.session_state.scores['Authority']}/100")
    st.divider()
    st.subheader("🔢 Token Usage")
    c1, c2 = st.columns(2)
    with c1: st.metric("Input",  f"{st.session_state.total_input_tokens:,}")
    with c2: st.metric("Output", f"{st.session_state.total_output_tokens:,}")
    st.metric("💰 Session Cost", f"${st.session_state.total_cost:.4f}")
    st.caption("Gemini 2.5 Pro: $1.25/1M input · $10.00/1M output")
    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost = 0.0
        st.rerun()

# ── Main UI ───────────────────────────────────────────────────
st.title("🚀 GEO Content Auditor")
st.write("Paste a **URL** or **Text** below to audit its optimization for AI search engines.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Core Logic ────────────────────────────────────────────────
if prompt := st.chat_input("Enter URL (starting with http) or paste content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    content_to_analyze = prompt
    if prompt.strip().startswith("http"):
        with st.status("🔍 Reading website..."):
            content_to_analyze = extract_website_text(prompt)
            if "Error scraping" in content_to_analyze:
                st.error(content_to_analyze)
                st.stop()

    try:
        SYSTEM = """
You are a GEO (Generative Engine Optimisation) expert.

⚠️ RULES:
- Only use facts already on the page. Never invent statistics, names, or results.
- For missing info write [DATA NEEDED: description]
- For missing case study results write: "Case Study: How [client type] improved [outcome] — add your real result here"

Return your response as a JSON object with exactly these keys:

{
  "brand": "brand or company name from the page",
  "hero_title": "rewritten main headline as a bold claim or question",
  "hero_sub": "1-2 sentence subheading, answer-first",
  "hero_cta": "call to action button text",
  "what_heading": "heading as a natural language question about what the service is",
  "what_body": "2-4 paragraphs defining GEO and the service. Define terms on first use.",
  "how_heading": "heading as a natural language question about how it works",
  "how_body": "2-4 paragraphs explaining the process. Use [DATA NEEDED] where info is missing.",
  "results_heading": "heading as a question about results or proof",
  "results_items": [
    {"title": "Case study or result title", "body": "description or placeholder"},
    {"title": "Second result title", "body": "description or placeholder"}
  ],
  "about_heading": "heading as a question about who the agency is",
  "about_body": "2-3 paragraphs. Use [DATA NEEDED] for missing author/credentials.",
  "data_gaps": [
    "Plain English description of each piece of missing content the client needs to provide"
  ],
  "colours": {
    "bg": "darkest hex colour from CSS context or #0f172a",
    "card": "second darkest hex or #1e293b",
    "accent": "most vivid/bright hex colour or #6366f1",
    "text": "lightest hex or #e2e8f0",
    "muted": "mid-tone text hex or #94a3b8",
    "border": "subtle border hex or #334155"
  },
  "changes": [
    "Bullet point 1 explaining what was restructured",
    "Bullet point 2",
    "Bullet point 3"
  ],
  "scores": {"read": 75, "facts": 40, "auth": 30}
}

Return ONLY the JSON. No markdown. No explanation. No code fences.
"""

        with st.status("🧠 Analysing and restructuring content..."):
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                config={"system_instruction": SYSTEM},
                contents=[{"role": "user", "parts": [{"text": content_to_analyze}]}]
            )
            raw = response.text.strip()

            # Token tracking
            try:
                usage = response.usage_metadata
                st.session_state.total_input_tokens  += usage.prompt_token_count or 0
                st.session_state.total_output_tokens += usage.candidates_token_count or 0
                st.session_state.total_cost += (
                    (usage.prompt_token_count or 0) / 1_000_000 * 1.25 +
                    (usage.candidates_token_count or 0) / 1_000_000 * 10.00
                )
            except Exception:
                pass

        # Strip code fences if model added them
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$",       "", raw).strip()

        import json
        data = json.loads(raw)

        # Update scores
        try:
            scores = data.get("scores", {})
            st.session_state.scores["AI_Readability"] = str(scores.get("read",  0))
            st.session_state.scores["Fact_Density"]   = str(scores.get("facts", 0))
            st.session_state.scores["Authority"]       = str(scores.get("auth",  0))
        except Exception:
            pass

        # Extract colours from page CSS + model suggestion
        page_colours = extract_colours(content_to_analyze)
        model_colours = data.get("colours", {})
        final_colours = {**page_colours, **{k: v for k, v in model_colours.items() if v and v.startswith("#")}}

        # Build the HTML using Python template
        html_page = build_html_page(data, final_colours)

        # ── Render ─────────────────────────────────────────────
        changes   = data.get("changes",   [])
        data_gaps = data.get("data_gaps", [])

        summary_md = "### What Was Changed\n" + \
                     "\n".join([f"- {c}" for c in changes]) + \
                     "\n\n### Client To-Do List\n" + \
                     "\n".join([f"- {g}" for g in data_gaps])

        with st.chat_message("assistant"):
            st.markdown(summary_md)
            st.divider()
            st.subheader("🌐 GEO-Optimised Website Preview")
            st.caption("This is your restructured page. Scroll inside the frame to see the full design.")
            st.components.v1.html(html_page, height=1400, scrolling=True)
            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.info("👆 Scroll inside the preview to see the full page.")
            with col2:
                st.download_button(
                    label="⬇️ Download HTML File",
                    data=html_page,
                    file_name="geo_optimised_page.html",
                    mime="text/html",
                    use_container_width=True
                )
            with st.expander("👨‍💻 Raw HTML for your developer"):
                st.code(html_page, language="html")

        st.session_state.messages.append({"role": "assistant", "content": summary_md})
        st.rerun()

    except json.JSONDecodeError as e:
        st.error(f"JSON parse error: {e}")
        st.text(raw[:3000])
    except Exception as e:
        st.error(f"Error: {e}")
