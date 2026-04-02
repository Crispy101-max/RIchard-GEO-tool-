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

        # Grab CSS colour hints BEFORE stripping styles
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

# ── Input & AI Logic ──────────────────────────────────────────
if prompt := st.chat_input("Enter URL (starting with http) or paste content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    content_to_analyze = prompt
    if prompt.strip().startswith("http"):
        with st.status("Reading website content..."):
            content_to_analyze = extract_website_text(prompt)
            if "Error scraping" in content_to_analyze:
                st.error(content_to_analyze)
                st.stop()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            config={
                "system_instruction": """
⚠️ STRICT GROUNDING RULE — READ FIRST ⚠️
You must ONLY use information, facts, statistics, names, and claims that already exist in the provided page content.
- DO NOT invent statistics, percentages, or metrics
- DO NOT fabricate author names, credentials, or publication dates
- DO NOT create fictional client names or company details
- If a specific fact or figure is missing but would strengthen a section, insert: [DATA NEEDED: brief description]
- For case studies or results sections: if the page mentions a result, you may present it. If no result exists, write a placeholder card styled as: "Case Study: How [client type] improved [relevant outcome] — insert real client result here"
- Never write the actual numbers or outcomes yourself. Frame the structure, not the claim.

The content you receive is the ONLY source of truth. Your job is to RESTRUCTURE and REFRAME it, never invent it.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are an expert GEO strategist and web designer. Your job is to produce a single complete HTML webpage that shows what the client's website would look like after full GEO optimisation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — GEO CONTENT REWRITE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ANSWER-FIRST: Every section opens with its most important fact or answer.
2. QUESTION HEADERS: Convert headings to natural language questions mirroring AI queries.
3. ENTITY DEFINITIONS: Add a definitional sentence for key concepts on first mention.
4. PASSAGE CHUNKING: Break long paragraphs into 2-4 sentence retrievable blocks.
5. SPEAKABLE SENTENCES: Refine existing sentences to be self-contained and citation-ready.
6. E-E-A-T GAPS: Where credentials or dates are missing insert [DATA NEEDED: ...] — never invent.
7. REDUNDANCY REMOVAL: Remove filler. Replace empty sections with [DATA NEEDED] placeholders.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — FULL HTML PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Produce a single complete self-contained HTML file of the redesigned page.

1. COLOUR SCHEME: Use hex values extracted from the provided CSS context.
2. LAYOUT: Mirror the original page section structure and order exactly.
3. CONTENT: Use only rewritten content from Part 1.
4. DATA GAPS: Show red-bordered placeholder boxes labelled [DATA NEEDED] where content is missing.
5. CASE STUDIES: Use real results if they exist. If not, render a styled card: "Case Study: Discover how [client type] improved [relevant outcome] — insert your real result here."
6. TYPOGRAPHY: Clear hierarchy. System fonts only.
7. QUALITY: Real agency-level design. Proper spacing, card shadows, consistent visual rhythm.
8. RESPONSIVE: CSS flexbox or grid.
9. SELF-CONTAINED: Pure HTML and inline CSS only. No JavaScript. No external CDN links.
10. NO BADGES: Clean client-facing page. Developer notes in HTML comments only.

Wrap in:
||MOCKUP_START||
[complete HTML]
||MOCKUP_END||

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Brief summary of changes (150 words max)
2. List of DATA NEEDED items
3. HTML mockup in delimiters
4. Scores

||SCORES||
READ: [0-100]
FACTS: [0-100]
AUTH: [0-100]
""",
            },
            contents=[{"role": "user", "parts": [{"text": content_to_analyze}]}]
        )

        # ── Everything below is INSIDE the try block ──────────

        full_text = response.text

        # Token counter
        try:
            usage = response.usage_metadata
            input_tokens  = usage.prompt_token_count or 0
            output_tokens = usage.candidates_token_count or 0
            INPUT_COST_PER_1M  = 1.25
            OUTPUT_COST_PER_1M = 10.00
            call_cost = (input_tokens  / 1_000_000 * INPUT_COST_PER_1M) + \
                        (output_tokens / 1_000_000 * OUTPUT_COST_PER_1M)
            st.session_state.total_input_tokens  += input_tokens
            st.session_state.total_output_tokens += output_tokens
            st.session_state.total_cost          += call_cost
        except Exception:
            pass

        # Parse scores
        if "||SCORES||" in full_text:
            full_text, score_block = full_text.split("||SCORES||", 1)
            try:
                st.session_state.scores["AI_Readability"] = re.search(r"READ:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Fact_Density"]   = re.search(r"FACTS:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Authority"]       = re.search(r"AUTH:\s*(\d+)", score_block).group(1)
            except AttributeError:
                pass

        # Parse HTML mockup
        html_mockup = None
        if "||MOCKUP_START||" in full_text and "||MOCKUP_END||" in full_text:
            before, rest       = full_text.split("||MOCKUP_START||", 1)
            html_mockup, after = rest.split("||MOCKUP_END||", 1)
            html_mockup        = html_mockup.strip()
            display_text       = (before + after).strip()
        else:
            display_text = full_text.strip()

        # Render output
        with st.chat_message("assistant"):
            st.markdown(display_text)

            if html_mockup:
                st.divider()
                st.subheader("🌐 Your GEO-Optimised Website Preview")
                st.caption("Scroll within the frame to see the full design.")
                st.components.v1.html(html_mockup, height=1200, scrolling=True)
                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.info("👆 Scroll the preview above to see the full page.")
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
                st.warning("No mockup was generated. Try submitting the URL again.")

        st.session_state.messages.append({"role": "assistant", "content": display_text})
        st.rerun()

    except Exception as e:
        st.error(f"Analysis Error: {e}")
