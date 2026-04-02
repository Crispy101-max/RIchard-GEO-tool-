import streamlit as st
import streamlit.components.v1 as components
from google import genai
import re
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# -----------------------------
# App / API setup
# -----------------------------
st.set_page_config(page_title="GEO Content Auditor", layout="wide")
client = genai.Client(api_key=st.secrets["API_Key"])

HEX_PATTERN = re.compile(r'#[0-9a-fA-F]{3,8}\b')


# -----------------------------
# Helpers
# -----------------------------
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_hex_colours(css_text: str, inline_styles: list[str]) -> list[str]:
    combined = css_text + "\n" + "\n".join(inline_styles)
    colours = HEX_PATTERN.findall(combined)

    # Normalise and dedupe while preserving order
    seen = set()
    cleaned = []
    for c in colours:
        c = c.lower()
        if len(c) == 4:  # #abc -> #aabbcc
            c = "#" + "".join([x * 2 for x in c[1:]])
        if c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned[:8]


def domain_to_brand(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.replace("www.", "")
        brand = netloc.split(".")[0]
        return brand.replace("-", " ").replace("_", " ").title()
    except Exception:
        return "Brand"


def extract_website_data(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else domain_to_brand(url)

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    # Keep style info before removing tags
    style_tags = soup.find_all("style")
    css_text = "\n".join([s.get_text(" ", strip=True) for s in style_tags])

    inline_styles = []
    for tag in soup.find_all(style=True):
        style_val = tag.get("style", "")
        if "color" in style_val.lower() or "background" in style_val.lower():
            inline_styles.append(style_val)

    colours = extract_hex_colours(css_text, inline_styles)

    # Grab headings for structure clues
    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        txt = clean_whitespace(h.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    # Remove junk for text extraction
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))

    # Limit text size to avoid excessive token use
    page_text = page_text[:25000]

    return {
        "url": url,
        "title": title,
        "brand_name": domain_to_brand(url),
        "meta_description": meta_description,
        "headings": headings[:20],
        "page_text": page_text,
        "colours": colours,
        "raw_css_excerpt": css_text[:4000],
        "inline_styles_excerpt": inline_styles[:20],
    }


def parse_json_from_model(text: str) -> dict:
    """
    Safely parse JSON even if the model wraps it in markdown fences.
    """
    cleaned = text.strip()

    # Remove code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # Try full parse first
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Fallback: extract from first { to last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start:end + 1]
        return json.loads(snippet)

    raise ValueError("Could not parse valid JSON from model response.")


def clean_html_output(html_raw: str) -> str:
    html_raw = html_raw.strip()

    # Remove markdown fences
    if html_raw.startswith("```"):
        html_raw = re.sub(r"^```(?:html)?\s*", "", html_raw)
        html_raw = re.sub(r"\s*```$", "", html_raw)

    return html_raw.strip()


def html_looks_valid(html_raw: str) -> bool:
    lowered = html_raw.strip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html")


def add_usage_to_session(response):
    try:
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0

        st.session_state.total_input_tokens += prompt_tokens
        st.session_state.total_output_tokens += output_tokens

        # Gemini 2.5 Pro pricing used from your original code
        st.session_state.total_cost += (prompt_tokens / 1_000_000 * 1.25) + \
                                       (output_tokens / 1_000_000 * 10.00)
    except Exception:
        pass


def call_gemini(user_text: str, system_instruction: str):
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        config={"system_instruction": system_instruction},
        contents=[{"role": "user", "parts": [{"text": user_text}]}]
    )
    return response


# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "scores" not in st.session_state:
    st.session_state.scores = {
        "AI_Readability": "0",
        "Fact_Density": "0",
        "Authority": "0"
    }

if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0

if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0


# -----------------------------
# Sidebar
# -----------------------------
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
        st.session_state.scores = {
            "AI_Readability": "0",
            "Fact_Density": "0",
            "Authority": "0"
        }
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.total_cost = 0.0
        st.rerun()


# -----------------------------
# UI
# -----------------------------
st.title("🚀 GEO Content Auditor")
st.write(
    "Paste a **URL** or **Text** below to audit its optimisation for AI search engines, "
    "rewrite it for GEO, and preview a visual mock webpage."
)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# -----------------------------
# Main flow
# -----------------------------
if prompt := st.chat_input("Enter URL (starting with http) or paste website content..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Step 0: Load source
    source_data = None
    content_to_analyze = prompt
    source_mode = "text"

    if prompt.strip().startswith("http"):
        source_mode = "url"
        with st.status("🔍 Reading website..."):
            try:
                source_data = extract_website_data(prompt)
                content_to_analyze = source_data["page_text"]

                if not content_to_analyze.strip():
                    st.error("The page was fetched but no readable text content was found.")
                    st.stop()

            except Exception as e:
                st.error(f"Error scraping {prompt}: {str(e)}")
                st.stop()
    else:
        # Pasted text mode
        source_data = {
            "url": "",
            "title": "Pasted Content",
            "brand_name": "Brand",
            "meta_description": "",
            "headings": [],
            "page_text": clean_whitespace(prompt)[:25000],
            "colours": [],
            "raw_css_excerpt": "",
            "inline_styles_excerpt": [],
        }

    try:
        # -----------------------------
        # CALL 1: GEO audit + rewritten content (JSON)
        # -----------------------------
        analysis_system = """
You are a senior Generative Engine Optimisation (GEO) strategist.

Your task:
1. Assess what prevents the page from being GEO-optimised.
2. Rewrite the page so it is GEO-optimised.
3. Keep the content and meaning roughly the same.
4. Improve structure, headings, chunking, clarity, answer-first delivery, entity definitions, and trust signals.
5. NEVER invent facts, statistics, credentials, case studies, or results.
6. If required information is missing, insert placeholders exactly in this format:
   [DATA NEEDED: short description]

IMPORTANT RULES:
- Only use facts already present in the source content.
- If the source page is thin, create a stronger structure using the existing meaning.
- Keep it commercially usable and realistic.
- Do not output commentary outside valid JSON.

Return VALID JSON only in exactly this structure:
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

        analysis_user = f"""
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
- Use question-style headings where appropriate.
- Start sections with the most important answer/fact.
- Define key terms on first mention.
- Break long paragraphs into short 2-4 sentence blocks.
- Remove vague filler.
- Preserve the page's original commercial intent.
- Add [DATA NEEDED: ...] where specifics are missing.
- Make the content suitable for AI search engines.
"""

        with st.status("🧠 Step 1/2 — Auditing and rewriting content..."):
            analysis_response = call_gemini(analysis_user, analysis_system)
            add_usage_to_session(analysis_response)
            analysis_json = parse_json_from_model(analysis_response.text)

        # Validate/fallback
        changes_made = analysis_json.get("changes_made", [])
        rewritten_content = analysis_json.get("rewritten_content", "").strip()
        data_gaps = analysis_json.get("data_gaps", [])
        scores = analysis_json.get("scores", {})

        if not rewritten_content:
            st.error("The model did not return rewritten content.")
            st.stop()

        st.session_state.scores["AI_Readability"] = str(scores.get("readability", 0))
        st.session_state.scores["Fact_Density"] = str(scores.get("fact_density", 0))
        st.session_state.scores["Authority"] = str(scores.get("authority", 0))

        # Build audit display text
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

        # -----------------------------
        # CALL 2: HTML mock webpage
        # -----------------------------
        palette = source_data["colours"] if source_data["colours"] else [
            "#0f172a", "#1e293b", "#6366f1", "#e2e8f0"
        ]

        html_system = """
You are a professional website designer.

Your ONLY job is to produce a complete HTML webpage for visual mockup purposes.

RULES:
- Output ONLY raw HTML.
- Do not include markdown fences.
- Do not include any commentary.
- Start with <!DOCTYPE html> and end with </html>.
- No JavaScript.
- No external fonts.
- No external image URLs.
- Use CSS only.
- The page must look polished and realistic, not like a wireframe.
- The mockup is for visualisation only.
"""

        html_user = f"""
Create a fully responsive, professional HTML mock webpage using the GEO-rewritten content below.

GOAL:
- This is a visual mockup of the improved page.
- Keep the original theme/style direction as much as possible.
- Use the original page colours where available.
- Reflect a cleaner GEO-optimised structure.
- Show [DATA NEEDED: ...] items as red dashed placeholder boxes.

BRAND NAME:
{source_data["brand_name"]}

PAGE TITLE:
{source_data["title"]}

ORIGINAL URL:
{source_data["url"]}

ORIGINAL HEADINGS:
{json.dumps(source_data["headings"], ensure_ascii=False)}

COLOUR PALETTE TO USE:
{json.dumps(palette)}

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
- Include a strong hero section
- Include all sections present in the rewritten content
- Preserve the section order from the rewritten content
- Use cards, spacing, hierarchy, and subtle shadows
- Use system fonts only
- Make it modern and conversion-friendly
- Footer at bottom
- If a section contains [DATA NEEDED: ...], display it in a clearly styled red dashed box
- If the page is text-heavy, make it visually appealing with alternating sections, cards, highlighted key points, and clean layout
- No lorem ipsum
- No fake client results
- No fake testimonials

Return raw HTML only.
"""

        with st.status("🎨 Step 2/2 — Building mock webpage..."):
            html_response = call_gemini(html_user, html_system)
            add_usage_to_session(html_response)
            html_raw = clean_html_output(html_response.text)

        # -----------------------------
        # Render result
        # -----------------------------
        with st.chat_message("assistant"):
            st.markdown(display_text)

            st.divider()
            st.subheader("🌐 GEO-Optimised Website Preview")

            if html_looks_valid(html_raw):
                st.caption("Scroll inside the frame to view the redesigned mock page.")
                components.html(html_raw, height=1400, scrolling=True)

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
                st.error("HTML mockup could not be generated as valid HTML. Raw output below:")
                st.text(html_raw[:3000])

        st.session_state.messages.append({
            "role": "assistant",
            "content": display_text
        })

        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
