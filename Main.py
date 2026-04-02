import streamlit as st
import streamlit.components.v1 as components
from google import genai
import re
import requests
from bs4 import BeautifulSoup

client = genai.Client(api_key=st.secrets["API_Key"])

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

def call_gemini(prompt_text, system_instruction):
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        config={"system_instruction": system_instruction},
        contents=[{"role": "user", "parts": [{"text": prompt_text}]}]
    )
    return response

# ── Session State ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scores" not in st.session_state:
    st.session_state.scores = {"AI_Readability": "0", "Fact_Density": "0", "Authority": "0"}
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
    st.metric("Fact Density", f"{st.session_state.scores['Fact_Density']}%")
    st.metric("Entity Authority", f"{st.session_state.scores['Authority']}/100")
    st.divider()
    st.subheader("🔢 Token Usage")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Input", f"{st.session_state.total_input_tokens:,}")
    with col2:
        st.metric("Output", f"{st.session_state.total_output_tokens:,}")
    st.metric("💰 Session Cost", f"${st.session_state.total_cost:.4f}")
    st.caption("Gemini 2.5 Pro: $1.25/1M input · $10.00/1M output")
    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost = 0.0
        st.rerun()

# ── Main Interface ────────────────────────────────────────────
st.title("🚀 GEO Content Auditor")
st.write("Paste a **URL** or **Text** below to audit its optimization for AI search engines.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input & AI Logic ──────────────────────────────────────────
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
        # ── CALL 1: Analysis + rewritten copy ─────────────────
        ANALYSIS_PROMPT = """
You are a GEO (Generative Engine Optimisation) strategist.

⚠️ STRICT RULE: Only use facts already on the page. Never invent statistics, names, or results.
If something is missing, write [DATA NEEDED: description].

Analyse the page content provided and return:

1. CHANGES MADE
A bullet list (max 5 points) of what you would restructure and why.

2. GEO-REWRITTEN CONTENT
Rewrite the page content applying these rules:
- ANSWER-FIRST: Every section opens with its most important fact
- QUESTION HEADERS: All headings become natural language questions
- ENTITY DEFINITIONS: Define every key term on first mention
- PASSAGE CHUNKING: Break paragraphs into 2-4 sentence blocks
- REMOVE FILLER: Delete vague marketing language, replace with [DATA NEEDED] if section empties
- E-E-A-T: Where author/date/credentials missing, insert [DATA NEEDED: add author name etc]
- CASE STUDIES: If no real result exists write "Case Study: How [client type] improved [outcome] — add your real result here"

3. DATA GAPS LIST
Bullet list of every [DATA NEEDED] item so client knows exactly what to provide.

4. Scores at the very end:
||SCORES||
READ: [0-100]
FACTS: [0-100]
AUTH: [0-100]
"""

        with st.status("🧠 Step 1/2 — Analysing page and rewriting content..."):
            analysis_response = call_gemini(content_to_analyze, ANALYSIS_PROMPT)
            analysis_text = analysis_response.text

            try:
                usage = analysis_response.usage_metadata
                st.session_state.total_input_tokens  += usage.prompt_token_count or 0
                st.session_state.total_output_tokens += usage.candidates_token_count or 0
                st.session_state.total_cost += ((usage.prompt_token_count or 0) / 1_000_000 * 1.25) + \
                                               ((usage.candidates_token_count or 0) / 1_000_000 * 10.00)
            except Exception:
                pass

        # Parse scores from analysis
        if "||SCORES||" in analysis_text:
            analysis_text, score_block = analysis_text.split("||SCORES||", 1)
            try:
                st.session_state.scores["AI_Readability"] = re.search(r"READ:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Fact_Density"]   = re.search(r"FACTS:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Authority"]       = re.search(r"AUTH:\s*(\d+)", score_block).group(1)
            except AttributeError:
                pass

        # ── CALL 2: HTML mockup only ───────────────────────────
        HTML_PROMPT = f"""
You are a professional web designer. Your ONLY job is to produce a complete HTML webpage.

Do not write any explanation, summary, or text outside the HTML.
Output ONLY the raw HTML file, nothing else — no markdown, no commentary.

Use this GEO-rewritten content to build the page:

{analysis_text}

Also use this original page data for the colour scheme:

{content_to_analyze}

HTML REQUIREMENTS:
- Complete file from <!DOCTYPE html> to </html>
- Extract real hex colours from the CSS context in the original page data. Use them exactly.
- If no colours found, use: background #0f172a, cards #1e293b, accent #6366f1, text #e2e8f0
- Mirror the original page's section structure and order
- Hero section with large headline and CTA button
- Navigation bar at top with logo/brand name
- All sections from the rewritten content
- [DATA NEEDED] items styled as red dashed border boxes
- Cards with subtle shadows, proper spacing, clear visual hierarchy
- System fonts only (no Google Fonts)
- No JavaScript
- No external image URLs — use CSS gradients for backgrounds
- Fully responsive using CSS flexbox or grid
- Footer at bottom
- Must look like a real professional website, not a wireframe

Output the raw HTML only. Start your response with <!DOCTYPE html> and end with </html>.
"""

        with st.status("🎨 Step 2/2 — Building visual mockup..."):
            html_response = call_gemini(content_to_analyze, HTML_PROMPT)
            html_raw = html_response.text.strip()

            try:
                usage = html_response.usage_metadata
                st.session_state.total_input_tokens  += usage.prompt_token_count or 0
                st.session_state.total_output_tokens += usage.candidates_token_count or 0
                st.session_state.total_cost += ((usage.prompt_token_count or 0) / 1_000_000 * 1.25) + \
                                               ((usage.candidates_token_count or 0) / 1_000_000 * 10.00)
            except Exception:
                pass

        # Clean the HTML — strip markdown code fences if model added them
        if html_raw.startswith("```"):
            html_raw = re.sub(r"^```[a-z]*\n?", "", html_raw)
            html_raw = re.sub(r"\n?```$", "", html_raw)
        html_raw = html_raw.strip()

        # ── Render everything ──────────────────────────────────
        display_text = analysis_text.strip()

        with st.chat_message("assistant"):
            st.markdown(display_text)

            if html_raw.startswith("<!DOCTYPE") or html_raw.startswith("<html"):
                st.divider()
                st.subheader("🌐 GEO-Optimised Website Preview")
                st.caption("Scroll inside the frame to see the full redesigned page.")
                st.components.v1.html(html_raw, height=1400, scrolling=True)
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.info("👆 Scroll inside the preview above to see the full page.")
                with col2:
                    st.download_button(
                        label="⬇️ Download HTML File",
                        data=html_raw,
                        file_name="geo_optimised_page.html",
                        mime="text/html",
                        use_container_width=True
                    )

                with st.expander("👨‍💻 Raw HTML for your developer"):
                    st.code(html_raw, language="html")
            else:
                st.error("HTML mockup could not be generated. Raw output below:")
                st.text(html_raw[:2000])

        st.session_state.messages.append({"role": "assistant", "content": display_text})
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
