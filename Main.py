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
            model="gemini-2.5-Pro", # Using the current stable flash model
            config={
                "system_instruction": """
                **Role:** Expert GEO (Generative Engine Optimization) Strategist. Your goal is to rewrite and structure the content on a webpage to optiimse it for visibility on LLMs
                
                **Analysis Goal:** Critique the text for 'Extractability' (how easily an AI finds facts) and 'Authority'.
                
                **Style Guide:** - Identify 'fluff' that should be replaced with data.
                - Suggest H2 headers that function as questions.
                - Check for Schema.org opportunities.
                
                **Required Output:** Provide your critique, then end with:
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
