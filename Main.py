import streamlit as st
from google import genai
import re
import requests
from bs4 import BeautifulSoup

# Initialize Gemini Client
client = genai.Client(api_key=st.secrets["API_Key"])

# Helper function to extract clean text from a URL
def extract_website_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Pretend to be a browser
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"

# 1. Setup App State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scores" not in st.session_state:
    st.session_state.scores = {"AI_Readability": "0", "Fact_Density": "0", "Authority": "0"}

# 2. Sidebar: The GEO Scoreboard
with st.sidebar:
    st.title("📊 GEO Scoreboard")
    st.metric("AI Readability", f"{st.session_state.scores['AI_Readability']}/100")
    st.metric("Fact Density", f"{st.session_state.scores['Fact_Density']}%")
    st.metric("Entity Authority", f"{st.session_state.scores['Authority']}/100")
    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# 3. Main Interface
st.title("🚀 GEO Content Auditor")
st.write("Paste a **URL** or **Text** below to audit its optimization for AI search engines.")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Input & AI Logic
if prompt := st.chat_input("Enter URL (starting with http) or paste content..."):
    # UI: Add user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Web Scraping Logic
    content_to_analyze = prompt
    if prompt.strip().startswith("http"):
        with st.status("Reading website content..."):
            content_to_analyze = extract_website_text(prompt)
            if "Error scraping" in content_to_analyze:
                st.error(content_to_analyze)
                st.stop()

    # API Call with GEO System Instructions
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro", # Using the current stable flash model
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

You are an expert GEO strategist and web designer. Your job is to produce a single complete HTML webpage that shows what the client's website would look like after full GEO optimisation. This is a visual deliverable — a realistic, polished redesign the client can actually see and hand to their developer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — GEO CONTENT REWRITE (internal, feeds into mockup)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before building the mockup, apply these rewrites to the source content:

1. ANSWER-FIRST: Every section opens with its most important fact or answer. Restructure existing sentences — do not add new facts.

2. QUESTION HEADERS: Convert all headings to natural language questions that mirror how users query AI assistants. Base them only on what the page actually covers.

3. ENTITY DEFINITIONS: On first mention of any key concept, product, or service already named on the page, add a single clear definitional sentence.

4. PASSAGE CHUNKING: Break long paragraphs into 2-4 sentence blocks, each answering one specific question. No new information added.

5. SPEAKABLE SENTENCES: Identify or lightly refine existing sentences that are self-contained and fact-dense enough for AI to cite directly.

6. E-E-A-T GAPS: Where author names, dates, or credentials are missing, insert styled placeholder boxes labelled [DATA NEEDED: e.g. Add author name and credentials here] — never invent these.

7. REDUNDANCY REMOVAL: Remove marketing filler. If a section becomes empty, replace it with a [DATA NEEDED] placeholder.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — FULL HTML PAGE (the main output)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Produce a single, complete, self-contained HTML file that a client could open in a browser and see their improved website. This must feel like a real finished webpage, not a wireframe.

DESIGN RULES:

1. COLOUR SCHEME: Extract the real colour palette from the provided CSS context. Use those exact hex values. If colours cannot be determined, use a clean professional dark palette and state your assumption in an HTML comment.

2. LAYOUT: Mirror the original page's section structure and order exactly. Same sections, same hierarchy — just better content and design quality.

3. CONTENT: Use only the GEO-rewritten content from Part 1. Where gaps exist, show a styled red-bordered placeholder box with the [DATA NEEDED] label so the client knows exactly what to fill in.

4. CASE STUDIES: If the original page has a results or case study section, render it as a properly designed card or panel. Use the real result if it exists on the page. If no real result exists, render the card with this copy: "Case Study: Discover how [describe the type of client from the page] improved their [relevant outcome e.g. AI search visibility / organic reach / citation rate] — insert your real client result here." Style it as a genuine case study card, not a placeholder.

5. TYPOGRAPHY: Use a clear visual hierarchy — large hero headline, medium section headings, normal body text. Use system fonts only.

6. QUALITY: This must look like a real agency has designed it. Use proper spacing, subtle backgrounds, card shadows, and a consistent visual rhythm throughout.

7. RESPONSIVE: CSS flexbox or grid. Looks good at desktop width, does not break on mobile.

8. SELF-CONTAINED: Pure HTML and inline CSS only. No JavaScript. No external CDN links. No images that require external URLs — use CSS gradients or SVG patterns for any visual backgrounds.

9. NO BADGES OR ANNOTATIONS: The output is a clean client-facing page. Do not include any GEO annotation badges, colour dot systems, or developer notes visible on the page. Any notes for the developer should be in HTML comments only.

Wrap the entire HTML file in these exact delimiters:

||MOCKUP_START||
[complete HTML here]
||MOCKUP_END||

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT ORDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Brief written summary of what was changed and why (markdown, 150 words max)
2. List of DATA NEEDED items the client must fill in
3. HTML mockup wrapped in delimiters
4. Scores

||SCORES||
READ: [0-100]
FACTS: [0-100]
AUTH: [0-100]
""",
            },
            contents=[{"role": "user", "parts": [{"text": content_to_analyze}]}]
        )

        full_text = response.text
full_text = response.text

# Token counting
try:
    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count or 0
    output_tokens = usage.candidates_token_count or 0
    INPUT_COST_PER_1M  = 1.25
    OUTPUT_COST_PER_1M = 10.00
    call_cost = (input_tokens / 1_000_000 * INPUT_COST_PER_1M) + \
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

# Render the written summary
with st.chat_message("assistant"):
    st.markdown(display_text)

    if html_mockup:
        st.divider()
        st.subheader("🌐 Your GEO-Optimised Website Preview")
        st.caption("This is a live preview of your rewritten page. Scroll within the frame to see the full design.")
        
        # Render the actual page visually - tall enough to feel like a real site
        st.components.v1.html(html_mockup, height=1200, scrolling=True)
        
        st.divider()
        
        # Two columns: copy button context + download
        col1, col2 = st.columns(2)
        with col1:
            st.info("👆 Scroll the preview above to see the full page design.")
        with col2:
            st.download_button(
                label="⬇️ Download HTML File",
                data=html_mockup,
                file_name="geo_optimised_page.html",
                mime="text/html",
                use_container_width=True
            )
        
        # Expandable raw HTML for developers
        with st.expander("👨‍💻 View Raw HTML (for your developer)"):
            st.code(html_mockup, language="html")

st.session_state.messages.append({"role": "assistant", "content": display_text})
st.rerun()
        
        # Parse the scores for the sidebar
        if "||SCORES||" in full_text:
            parts = full_text.split("||SCORES||")
            display_text = parts[0].strip()
            score_block = parts[1]
            
            # Update the sidebar metrics using Regex
            try:
                st.session_state.scores["AI_Readability"] = re.search(r"READ:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Fact_Density"] = re.search(r"FACTS:\s*(\d+)", score_block).group(1)
                st.session_state.scores["Authority"] = re.search(r"AUTH:\s*(\d+)", score_block).group(1)
            except AttributeError:
                pass # Fallback if regex fails
        else:
            display_text = full_text

        with st.chat_message("assistant"):
            st.markdown(display_text)
        
        st.session_state.messages.append({"role": "assistant", "content": display_text})
        st.rerun()

    except Exception as e:
        st.error(f"Analysis Error: {e}")
