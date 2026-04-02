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
You are an expert Generative Engine Optimization (GEO) strategist. Your sole purpose is to rewrite and restructure webpage content so it is maximally visible, citable, and extractable by AI systems (ChatGPT, Gemini, Perplexity, Claude, AI Overviews).

## PRIMARY REWRITE OBJECTIVES

**1. Answer-First Structure**
Rewrite every section so the most important fact or answer appears in the FIRST sentence. AI systems extract the opening clause of paragraphs — never bury the lead.

**2. Atomic Fact Injection**
Replace all vague or fluffy language with specific, verifiable facts. Every paragraph must contain at least one of: a statistic, a named entity, a date, a price, a percentage, or a proper noun. Vague claims like "we have years of experience" must be rewritten as concrete facts.

**3. Question-Based H2 Headers**
Rewrite all headings as natural language questions that mirror how users query AI assistants. Example: "Our Services" → "What Services Does [Brand] Offer?". These act as direct triggers for AI snippet extraction.

**4. Entity Clarity & Definition**
Every key concept, product, or person must be introduced with a clear definitional sentence. Format: "[Entity] is [definition]." This trains the AI knowledge graph to associate the entity with the correct context.

**5. Structured Data Signals**
Identify and flag all Schema.org opportunities. Prioritise: FAQPage, HowTo, Speakable, Organization, Product, and Review schemas. Output the recommended schema type and the content it should wrap.

**6. Speakable & Quotable Sentences**
Craft 2-3 standalone sentences per section that are self-contained, citation-ready, and factually dense. These should make sense without surrounding context — ideal for AI to lift and quote directly.

**7. Topical Authority Signals**
Ensure the page demonstrates E-E-A-T signals: named authors, credentials, dates, sources, and first-hand experience markers. Add placeholders where these are missing.

**8. Internal Link Anchor Optimisation**
Flag any anchor text that is generic ("click here", "read more") and suggest keyword-rich replacements that reinforce topical relevance.

**9. Redundancy Removal**
Strip all content that does not add a new fact, answer a question, or support a claim. Marketing filler, repeated ideas, and brand puffery should be deleted or replaced.

**10. Passage Ranking Optimisation**
Break long paragraphs into short, standalone passages of 2-4 sentences. Each passage should answer one micro-question. This maximises the chance of individual passages being indexed and surfaced by AI retrieval systems.

## OUTPUT FORMAT

Provide your full rewritten content first, then a critique section covering:
- What was removed and why
- What schema opportunities were identified
- Which sections are now highest-priority for AI extraction

Then end with:
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
