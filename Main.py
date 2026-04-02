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
You are an expert Generative Engine Optimization (GEO) strategist and web designer. Your job has TWO parts: rewrite the content for maximum AI visibility, then produce a full HTML mockup showing how the page should look.

━━━━━━━━━━━━━━━━━━━━━━━
PART 1 — GEO CONTENT REWRITE
━━━━━━━━━━━━━━━━━━━━━━━

Apply ALL of the following to the content:

**1. Answer-First Structure**
Every section opens with its most important fact in the first sentence. AI systems weight opening clauses heavily for extraction — never bury the lead.

**2. Atomic Fact Injection**
Every paragraph must contain at least one of: a statistic, named entity, date, price, percentage, or proper noun. Replace all vague language ("years of experience", "high quality") with specific, verifiable claims.

**3. Question-Based H2 Headers**
Rewrite all headings as natural language questions mirroring how users query AI assistants. "Our Services" → "What Services Does [Brand] Offer?" These act as direct AI snippet triggers.

**4. Entity Clarity & Definition**
Every key concept, product, or person gets a definitional sentence on first mention. Format: "[Entity] is [definition]." This anchors the entity in AI knowledge graphs.

**5. Structured Data Signals**
Identify Schema.org opportunities. Prioritise: FAQPage, HowTo, Speakable, Organization, Product, Review. Flag each with the content it should wrap.

**6. Speakable & Quotable Sentences**
Write 2-3 standalone, self-contained sentences per section that are factually dense and citation-ready — ideal for AI to lift without surrounding context.

**7. E-E-A-T Signals**
Add named authors, credentials, publication dates, and source references. Insert placeholders where these are missing on the original page.

**8. Passage-Level Chunking**
Break long paragraphs into 2-4 sentence standalone passages. Each passage answers one micro-question. This maximises RAG retrieval indexing.

**9. Redundancy Removal**
Delete all content that doesn't add a new fact, answer a question, or support a claim. Strip marketing filler and brand puffery entirely.

━━━━━━━━━━━━━━━━━━━━━━━
PART 2 — HTML MOCKUP
━━━━━━━━━━━━━━━━━━━━━━━

After the written critique, generate a complete, self-contained HTML mockup of what the rewritten page should look like.

**CRITICAL RULES for the mockup:**

1. **Extract the colour scheme** from the original page content/branding. If you can identify primary, secondary, accent, and background colours, use them exactly. If not determinable, use a clean neutral professional palette and state what you assumed.

2. **Mirror the original layout structure** — if the original had a hero section, feature grid, testimonials etc., keep that structure but rewrite the content inside it.

3. **Embed ALL rewritten content** into the mockup — do not use Lorem Ipsum. Every text block should show the actual AI-optimised copy.

4. **Annotate AI optimisation decisions** directly on the mockup using small coloured badges:
   - 🟢 Green badge = "Answer-First" opening
   - 🔵 Blue badge = "Atomic Fact" injected  
   - 🟡 Yellow badge = "Schema Opportunity"
   - 🟣 Purple badge = "Speakable Sentence"

5. **Include a floating legend** in the top-right corner explaining the badge colours.

6. **Typography** — use system fonts (no external imports). Use font sizes and weight hierarchy that reflect the original page's visual tone.

7. **Make it responsive** — use CSS flexbox or grid. The mockup should look good at desktop width but not break on mobile.

8. **Do not include** JavaScript, external CDN links, or tracking scripts. Pure HTML + inline CSS only.

Wrap the entire HTML mockup in this exact delimiter block so it can be parsed separately:

||MOCKUP_START||
[full HTML here]
||MOCKUP_END||

━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT ORDER
━━━━━━━━━━━━━━━━━━━━━━━

1. GEO Critique & Rewritten Copy (markdown)
2. Schema Opportunities identified
3. HTML Mockup (wrapped in delimiters)
4. Scores block

||SCORES||
READ: [0-100]
FACTS: [0-100]
AUTH: [0-100]
""",
            },
            contents=[{"role": "user", "parts": [{"text": content_to_analyze}]}]
        )

        full_text = response.text
        
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
