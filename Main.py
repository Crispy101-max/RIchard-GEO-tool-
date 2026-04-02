import streamlit as st
import streamlit.components.v1 as components
from google import genai
import re
import requests
from bs4 import BeautifulSoup

# ── Gemini Client ─────────────────────────────────────────────
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
        if "html_mockup" in st.session_state and st.session_state.html_mockup:
            pass  # mockup re-render handled below

# ── Input & AI Logic ──────────────────────────────────────────
if prompt := st.chat_input("Enter URL (starting with http) or paste content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    content_to_analyze = prompt
    if prompt.strip().startswith("http"):
        with st.status("🔍 Reading website content..."):
            content_to_analyze = extract_website_text(prompt)
            if "Error scraping" in content_to_analyze:
                st.error(content_to_analyze)
                st.stop()

    try:
        with st.status("⚙️ Generating GEO-optimised mockup... this may take 30-60 seconds"):
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                config={
                    "system_instruction": """
You are an expert GEO (Generative Engine Optimisation) strategist and web designer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ ABSOLUTE RULES — NEVER BREAK THESE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Your PRIMARY and MOST IMPORTANT output is the HTML mockup. You MUST always produce it.
2. ONLY use facts, names, and claims already present in the page content provided.
3. NEVER invent statistics, percentages, author names, credentials, or client results.
4. Where information is missing but needed, insert a styled placeholder: [DATA NEEDED: description]
5. For case studies with no real data: write "Case Study: How [client type from page] improved [relevant outcome] — add your real result here" — never fabricate the result.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — ANALYSE THE PAGE (internal only, do not output this)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the page and identify:
- The colour scheme from the CSS context provided
- The page sections and layout structure
- What content exists vs what is missing
- What needs restructuring for GEO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — GEO REWRITES (internal only, feeds into HTML)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apply to all content before building the HTML:
- ANSWER-FIRST: Open every section with the most important fact
- QUESTION HEADERS: Rewrite all headings as natural language questions (e.g. "What does X do?" not "About X")
- ENTITY DEFINITIONS: Define every key term on first use in one sentence
- PASSAGE CHUNKING: Break long paragraphs into 2-4 sentence blocks
- REMOVE FILLER: Delete vague marketing language. Replace with [DATA NEEDED] if section becomes empty
- E-E-A-T: Where author, date, or credentials are missing, add [DATA NEEDED: add author name and credentials]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD THE HTML MOCKUP (THIS IS YOUR MAIN OUTPUT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Produce a COMPLETE, POLISHED, SELF-CONTAINED HTML file.

This is a visual client deliverable. It must look like a real finished professional website.

HTML RULES:
- Extract the real hex colour values from the CSS context and use them throughout
- If no colours found, use a clean dark professional palette (#0f172a background, #6366f1 accent)
- Mirror the original page section order and layout exactly
- Use the GEO-rewritten content from Step 2 — never original unoptimised text
- Style [DATA NEEDED] items as red dashed border boxes so clients see exactly what to fill in
- Use CSS flexbox or grid for layout
- System fonts only (no Google Fonts or CDN links)
- No JavaScript
- No external image URLs — use CSS gradients for hero backgrounds
- Proper spacing, shadows on cards, clear visual hierarchy
- Hero section with large headline, clear CTA button
- Navigation bar at top
- Footer at bottom
- Mobile responsive

CRITICAL: The HTML must be complete from <!DOCTYPE html> to </html>. Do not truncate it.

Wrap the ENTIRE HTML file in these exact tags on their own lines:
||MOCKUP_START||
[your complete HTML here]
||MOCKUP_END||

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR OUTPUT FORMAT — FOLLOW THIS EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output in this exact order:

**CHANGES MADE**
[3-5 bullet points summarising what was restructured and why — max 100 words total]

**DATA GAPS — CLIENT TO-DO LIST**
[Bullet list of every [DATA NEEDED] item so client knows what to provide]

[Then immediately output the HTML mockup wrapped in delimiters]

||MOCKUP_START||
[FULL HTML]
||MOCKUP_END||

||SCORES||
READ: [0-100]
FACTS: [0-100]
AUTH: [0-100]
""",
                },
                contents=[{"role": "user", "parts": [{"text": content_to_analyze}]}]
            )

        full_text = response.text

        # ── Token counter ──────────────────────────────────────
        try:
            usage = response.usage_metadata
            input_tokens  = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0
            call_cost = (input_tokens  / 1_000_000 * 1.25) + \
                        (output_tokens / 1_000_000 * 10.00)
            st.session_state.total_input_tokens  += input_tokens
            st.session_state.total_output_tokens += output_tokens
            st.session_state.total_cost          += call_cost
        except Exception:
            pass

        # ── Parse scores ───────────────────────────────────────
        if "||SCORES||" in full_text:
            full_text, score_block = full_text.split("||SCORES||", 1)
            try:
                st.session_state.scores["AI_Readability"] = re.search(r"READ:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Fact_Density"]   = re.search(r"FACTS:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Authority"]       = re.search(r"AUTH:\s*(\d+)", score_block).group(1)
            except AttributeError:
                pass

        # ── Parse HTML mockup ──────────────────────────────────
        html_mockup  = None
        display_text = full_text.strip()

        if "||MOCKUP_START||" in full_text and "||MOCKUP_END||" in full_text:
            before, rest       = full_text.split("||MOCKUP_START||", 1)
            html_mockup, after = rest.split("||MOCKUP_END||", 1)
            html_mockup        = html_mockup.strip()
            display_text       = (before + after).strip()
        else:
            # Fallback: try to find raw HTML if delimiters were dropped
            if "<!DOCTYPE html>" in full_text:
                idx         = full_text.index("<!DOCTYPE html>")
                html_mockup = full_text[idx:].strip()
                display_text = full_text[:idx].strip()

        # ── Render ─────────────────────────────────────────────
        with st.chat_message("assistant"):
            if display_text:
                st.markdown(display_text)

            if html_mockup:
                st.divider()
                st.subheader("🌐 GEO-Optimised Website Preview")
                st.caption("This is your restructured page. Scroll inside the frame to see the full design.")
                st.components.v1.html(html_mockup, height=1400, scrolling=True)
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.info("👆 Scroll inside the preview to see the full page.")
                with col2:
                    st.download_button(
                        label="⬇️ Download HTML File",
                        data=html_mockup,
                        file_name="geo_optimised_page.html",
                        mime="text/html",
                        use_container_width=True
                    )
                with st.expander("👨‍💻 View Raw HTML (for your developer)"):
                    st.code(html_mockup, language="html")
            else:
                st.warning("⚠️ The model did not return a visual mockup this time. Try submitting the URL again — Gemini occasionally drops the HTML block on complex pages.")
                with st.expander("🔍 Debug — raw model output"):
                    st.text(full_text[:3000])

        st.session_state.messages.append({"role": "assistant", "content": display_text})
        st.rerun()

    except Exception as e:
        st.error(f"Analysis Error: {e}")
