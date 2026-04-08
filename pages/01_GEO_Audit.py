import os
import json
import re
import html
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GEO Audit",
    page_icon="📋",
    layout="wide"
)

st.title("📋 GEO Audit")
st.write(
    "Audit the client's original page against target AI prompts and visualise the result "
    "as an annotated, clickable mockup of the original webpage."
)

# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key():
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass
    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()
if not API_KEY:
    st.error("No Gemini API key found. Add it as `API_Key` in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# Use Flash here to keep audit costs down
MODEL_NAME = "gemini-2.5-flash"

# ============================================================
# HELPERS
# ============================================================
HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_hex_colours(raw_html):
    colours = HEX_PATTERN.findall(raw_html or "")
    seen = set()
    ordered = []
    for c in colours:
        c = c.lower()
        if len(c) == 4:
            c = "#" + "".join(ch * 2 for ch in c[1:])
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered[:8]


def safe_json_parse(text):
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return valid JSON.")

    return json.loads(cleaned[start:end + 1])


def call_gemini_json(user_prompt, system_prompt):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0.1,
            top_k=1,
            candidate_count=1,
            max_output_tokens=8192,
            seed=42,
            system_instruction=system_prompt,
            response_mime_type="application/json"
        )
    )
    return safe_json_parse(response.text)


@st.cache_data(show_spinner=False)
def fetch_original_page(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    raw_html = r.text
    soup = BeautifulSoup(raw_html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else "Website"
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    nav_items = []
    nav = soup.find("nav")
    if nav:
        for a in nav.find_all("a"):
            txt = clean(a.get_text(" ", strip=True))
            if txt and len(txt) <= 30:
                nav_items.append(txt)

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        txt = clean(h.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    colours = extract_hex_colours(raw_html)

    # Remove obvious non-content elements before section extraction
    for element in soup(["script", "style", "footer", "noscript", "svg"]):
        element.decompose()

    body = soup.body if soup.body else soup

    sections = []
    current = {
        "section_id": "sec-0",
        "label": "Introduction",
        "content": []
    }
    section_count = 0

    for node in body.find_all(["h1", "h2", "h3", "p", "li"], recursive=True):
        if node.name in ["h1", "h2", "h3"]:
            heading_text = clean(node.get_text(" ", strip=True))
            if heading_text:
                if current["content"]:
                    sections.append(current)
                section_count += 1
                current = {
                    "section_id": f"sec-{section_count}",
                    "label": heading_text,
                    "content": []
                }
        else:
            txt = clean(node.get_text(" ", strip=True))
            if txt:
                current["content"].append(txt)

    if current["content"]:
        sections.append(current)

    # Fallback if extraction was too thin
    if not sections:
        all_text = clean(body.get_text(" ", strip=True))
        sections = [{
            "section_id": "sec-0",
            "label": title,
            "content": [all_text[:2500]]
        }]

    # keep reasonable size
    normalised = []
    for s in sections[:10]:
        joined = " ".join(s["content"])
        joined = joined[:2500]
        normalised.append({
            "section_id": s["section_id"],
            "label": s["label"],
            "content": joined
        })

    return {
        "title": title,
        "meta_description": meta_description,
        "nav_items": nav_items[:6],
        "headings": headings[:20],
        "colours": colours,
        "sections": normalised
    }


def section_score_class(avg_score):
    if avg_score >= 8:
        return "good"
    if avg_score >= 5:
        return "medium"
    return "poor"


def build_annotated_html(page_data, audit_data, company_name, target_prompts):
    sections = page_data["sections"]
    section_map = {s["section_id"]: s for s in sections}

    audit_sections = audit_data.get("sections", [])
    audit_lookup = {s["section_id"]: s for s in audit_sections}

    nav_items = page_data.get("nav_items", [])
    if not nav_items:
        nav_items = ["Overview", "Benefits", "Details", "Contact"]

    nav_html = "".join(
        [f'#{item.lower().replace(">{html.escape(item)}</a>' for item in nav_items]
    )

    prompt_chips = "".join([f'<span class="chip">{html.escape(p)}</span>' for p in target_prompts[:6]])

    rendered_sections = []

    for idx, section in enumerate(sections):
        audit_sec = audit_lookup.get(section["section_id"], {})
        readability = audit_sec.get("readability_score", 0)
        prompt_alignment = audit_sec.get("prompt_alignment_score", 0)
        helpfulness = audit_sec.get("human_helpfulness_score", 0)
        avg_score = round((readability + prompt_alignment + helpfulness) / 3, 1) if any([readability, prompt_alignment, helpfulness]) else 0
        cls = section_score_class(avg_score)

        issues = audit_sec.get("issues", [])
        improvements = audit_sec.get("improvements", [])
        related_prompts = audit_sec.get("related_prompts", [])

        issues_html = "".join([f"<li>{html.escape(i)}</li>" for i in issues])
        improvements_html = "".join([f"<li>{html.escape(i)}</li>" for i in improvements])
        related_html = "".join([f'<span class="mini-chip">{html.escape(p)}</span>' for p in related_prompts])

        content_paragraphs = ""
        content_text = section.get("content", "")
        split_paras = re.split(r"(?<=[.!?])\s+", content_text)
        for para in split_paras[:10]:
            para = para.strip()
            if para:
                content_paragraphs += f"<p>{html.escape(para)}</p>"

        section_anchor = section["label"].lower().replace(" ", "-")
        rendered_sections.append(f"""
        <section id="{section_anchor}" class="audit-section {cls}">
            <div class="section-top">
                <div>
                    <div class="section-kicker">Original page section</div>
                    <h2>{html.escape(section["label"])}</h2>
                </div>
                <div class="score-badge {cls}">Score {avg_score}/10</div>
            </div>

            <div class="score-row">
                <span>Readability: {readability}/10</span>
                <span>Prompt alignment: {prompt_alignment}/10</span>
                <span>Human helpfulness: {helpfulness}/10</span>
            </div>

            <div class="content-block">
                {content_paragraphs}
            </div>

            <details class="audit-note">
                <summary>Why this section needs attention</summary>
                <div class="note-grid">
                    <div class="note-card">
                        <h4>Issues</h4>
                        <ul>{issues_html}</ul>
                    </div>
                    <div class="note-card">
                        <h4>How to improve</h4>
                        <ul>{improvements_html}</ul>
                    </div>
                </div>
                <div class="related-prompts">
                    <strong>Related prompts:</strong> {related_html if related_html else "None listed"}
                </div>
            </details>
        </section>
        """)

    summary_cards = f"""
    <div class="summary-grid">
      <div class="summary-card">
        <h3>Audit focus</h3>
        <p>{html.escape(audit_data.get("overall_summary", ""))}</p>
      </div>
      <div class="summary-card">
        <h3>Target prompts</h3>
        <div class="chips">{prompt_chips}</div>
      </div>
    </div>
    """

    title = html.escape(page_data.get("title", "Website"))
    meta = html.escape(page_data.get("meta_description", ""))
    brand = html.escape(company_name or "Brand")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
:root {{
  --bg: #0f172a;
  --surface: #111827;
  --panel: #1f2937;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --accent: #6366f1;
  --good: #16a34a;
  --medium: #f59e0b;
  --poor: #ef4444;
  --shadow: 0 25px 60px rgba(0,0,0,.28);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: linear-gradient(180deg, var(--bg), #111827);
  color: var(--text);
  line-height: 1.6;
}}
.container {{
  width: min(1160px, calc(100% - 32px));
  margin: 0 auto;
}}
.nav {{
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255,255,255,.08);
}}
.nav-inner {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
}}
.brand {{
  font-weight: 700;
  color: white;
}}
.links {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}}
.links a {{
  color: var(--muted);
  text-decoration: none;
  font-size: .95rem;
}}
.hero {{
  padding: 64px 0 22px;
}}
.hero-card {{
  padding: 42px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(99,102,241,.18), transparent 35%),
    linear-gradient(135deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border: 1px solid rgba(255,255,255,.08);
  box-shadow: var(--shadow);
}}
.eyebrow {{
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(99,102,241,.18);
  color: #c7d2fe;
  font-size: .85rem;
  margin-bottom: 16px;
}}
.hero h1 {{
  font-size: clamp(2rem, 5vw, 3.7rem);
  line-height: 1.05;
  margin: 0 0 12px;
  color: white;
}}
.hero p {{
  max-width: 780px;
  color: var(--muted);
  margin: 0 0 22px;
}}
.summary-grid {{
  display: grid;
  gap: 18px;
  grid-template-columns: 1.2fr 1fr;
  margin: 24px 0 18px;
}}
.summary-card {{
  background: var(--panel);
  border-radius: 20px;
  padding: 22px;
  border: 1px solid rgba(255,255,255,.08);
  box-shadow: var(--shadow);
}}
.chips, .related-prompts {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.chip, .mini-chip {{
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
  color: #dbeafe;
  font-size: .85rem;
}}
.audit-shell {{
  display: grid;
  gap: 22px;
  grid-template-columns: 1fr;
  padding-bottom: 56px;
}}
.audit-section {{
  background: var(--panel);
  border-radius: 22px;
  padding: 28px;
  border: 2px solid rgba(255,255,255,.08);
  box-shadow: var(--shadow);
  position: relative;
}}
.audit-section.good {{
  border-color: rgba(22,163,74,.9);
}}
.audit-section.medium {{
  border-color: rgba(245,158,11,.9);
}}
.audit-section.poor {{
  border-color: rgba(239,68,68,.9);
}}
.section-top {{
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}}
.section-kicker {{
  color: var(--muted);
  font-size: .85rem;
  margin-bottom: 6px;
}}
.audit-section h2 {{
  color: white;
  margin: 0 0 6px;
}}
.score-badge {{
  min-width: 110px;
  text-align: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: 700;
  font-size: .9rem;
}}
.score-badge.good {{
  background: rgba(22,163,74,.16);
  color: #bbf7d0;
}}
.score-badge.medium {{
  background: rgba(245,158,11,.16);
  color: #fde68a;
}}
.score-badge.poor {{
  background: rgba(239,68,68,.16);
  color: #fecaca;
}}
.score-row {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin: 8px 0 16px;
  color: var(--muted);
  font-size: .92rem;
}}
.content-block p {{
  color: #cbd5e1;
  margin: 0 0 12px;
}}
.audit-note {{
  margin-top: 16px;
  border-top: 1px solid rgba(255,255,255,.08);
  padding-top: 14px;
}}
.audit-note summary {{
  cursor: pointer;
  color: #dbeafe;
  font-weight: 600;
}}
.note-grid {{
  display: grid;
  gap: 14px;
  grid-template-columns: 1fr 1fr;
  margin-top: 14px;
}}
.note-card {{
  background: rgba(255,255,255,.03);
  border-radius: 16px;
  padding: 16px;
  border: 1px solid rgba(255,255,255,.06);
}}
.note-card h4 {{
  margin: 0 0 10px;
  color: white;
}}
.note-card ul {{
  padding-left: 20px;
  margin: 0;
}}
.note-card li {{
  margin-bottom: 8px;
  color: #cbd5e1;
}}
.footer {{
  padding: 12px 0 48px;
  color: var(--muted);
  text-align: center;
}}
@media (max-width: 900px) {{
  .summary-grid,
  .note-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>
</head>
<body>
<nav class="nav">
  <div class="container nav-inner">
    <div class="brand">{brand}</div>
    <div class="links">{nav_html}</div>
  </div>
</nav>

<header class="hero">
  <div class="container">
    <div class="hero-card">
      <div class="eyebrow">Annotated GEO audit of the original page</div>
      <h1>{title}</h1>
      <p>{meta}</p>
    </div>
    {summary_cards}
  </div>
</header>

<main class="container audit-shell">
  {''.join(rendered_sections)}
</main>

<footer class="footer">
  <div class="container">Interactive audit preview generated from the original client page.</div>
</footer>
</body>
</html>
"""


# ============================================================
# LOAD FROM SHARED CONTEXT IF AVAILABLE
# ============================================================
default_url = ""
default_company = {
    "name": "",
    "industry": "",
    "niche": "",
    "target_customer": "",
    "goal": ""
}
default_prompts = []

if "geo_context" in st.session_state:
    geo = st.session_state.geo_context
    default_url = geo.get("url", "")
    default_company = geo.get("company", default_company)
    default_prompts = geo.get("target_prompts", [])

# ============================================================
# INPUTS
# ============================================================
st.subheader("1️⃣ Audit Inputs")
url = st.text_input("Website URL", value=default_url, placeholder="https://example.com")

col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input("Company name", value=default_company.get("name", ""))
    industry = st.text_input("Industry / category", value=default_company.get("industry", ""))
    niche = st.text_input("Niche", value=default_company.get("niche", ""))

with col2:
    target_customer = st.text_input("Target customer", value=default_company.get("target_customer", ""))
    goal = st.text_area("Business / AI goal", value=default_company.get("goal", ""), height=70)
    prompt_text = st.text_area(
        "Target AI prompts (one per line)",
        value="\n".join(default_prompts),
        height=140,
        placeholder="best skincare for sensitive skin\nbest moisturiser for eczema-prone skin"
    )

target_prompts = [p.strip() for p in prompt_text.splitlines() if p.strip()]

run = st.button("Run Interactive GEO Audit", type="primary", use_container_width=True)

# ============================================================
# MODEL PROMPT
# ============================================================
SYSTEM_PROMPT = """
You are a senior Generative Engine Optimisation auditor.

Your job is to audit a webpage section-by-section against a supplied target prompt set.

Focus on:
- human clarity
- answer-first structure
- whether each section helps an AI confidently answer the target prompts
- people-first helpfulness
- whether the section is too vague, too generic, or weakly aligned to the target prompts

Do NOT rewrite the content.
Do NOT invent facts.
Be direct, specific, and useful.

Return JSON ONLY in this structure:

{
  "overall_summary": "",
  "strengths": [],
  "weaknesses": [],
  "opportunities": [],
  "sections": [
    {
      "section_id": "",
      "section_label": "",
      "readability_score": 0,
      "prompt_alignment_score": 0,
      "human_helpfulness_score": 0,
      "related_prompts": [],
      "issues": [],
      "improvements": []
    }
  ],
  "priority_actions": []
}
"""

# ============================================================
# RUN
# ============================================================
if run:
    if not url.startswith("http"):
        st.error("Please enter a valid URL starting with http or https.")
        st.stop()

    try:
        with st.spinner("Reading original page..."):
            page_data = fetch_original_page(url)

        user_prompt = f"""
COMPANY:
{json.dumps({
    "name": company_name,
    "industry": industry,
    "niche": niche,
    "target_customer": target_customer,
    "goal": goal
}, ensure_ascii=False)}

TARGET PROMPTS:
{json.dumps(target_prompts, ensure_ascii=False)}

PAGE DATA:
{json.dumps(page_data, ensure_ascii=False)}
"""

        with st.spinner("Running section-by-section GEO audit..."):
            audit = call_gemini_json(user_prompt, SYSTEM_PROMPT)

        annotated_html = build_annotated_html(
            page_data=page_data,
            audit_data=audit,
            company_name=company_name,
            target_prompts=target_prompts
        )

        # Store in shared context if available / useful
        st.session_state.geo_context = {
            "url": url,
            "company": {
                "name": company_name,
                "industry": industry,
                "niche": niche,
                "target_customer": target_customer,
                "goal": goal,
            },
            "target_prompts": target_prompts,
            "page_snapshot": {
                "title": page_data["title"],
                "meta_description": page_data["meta_description"],
                "headings": page_data["headings"],
                "page_text": " ".join([s["content"] for s in page_data["sections"]])
            },
            "audit": audit,
            "mock_html": annotated_html
        }

        st.success("✅ Interactive audit generated.")

        tab1, tab2, tab3 = st.tabs([
            "🌐 Interactive Audit Page",
            "📋 Audit Summary",
            "👨‍💻 HTML Output"
        ])

        with tab1:
            components.html(annotated_html, height=1800, scrolling=True)

        with tab2:
            st.subheader("Overall Summary")
            st.write(audit.get("overall_summary", ""))

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("✅ Strengths")
                for item in audit.get("strengths", []):
                    st.write(f"- {item}")

            with col2:
                st.subheader("❌ Weaknesses")
                for item in audit.get("weaknesses", []):
                    st.write(f"- {item}")

            with col3:
                st.subheader("🚀 Opportunities")
                for item in audit.get("opportunities", []):
                    st.write(f"- {item}")

            st.subheader("Section Breakdown")
            for sec in audit.get("sections", []):
                with st.expander(f"{sec.get('section_label', '')}"):
                    st.write(f"**Readability:** {sec.get('readability_score', 0)}/10")
                    st.write(f"**Prompt alignment:** {sec.get('prompt_alignment_score', 0)}/10")
                    st.write(f"**Human helpfulness:** {sec.get('human_helpfulness_score', 0)}/10")

                    prompts = sec.get("related_prompts", [])
                    if prompts:
                        st.write("**Related prompts:**")
                        for p in prompts:
                            st.write(f"- {p}")

                    st.write("**Issues:**")
                    for i in sec.get("issues", []):
                        st.write(f"- {i}")

                    st.write("**Improvements:**")
                    for i in sec.get("improvements", []):
                        st.write(f"- {i}")

            st.subheader("Priority Actions")
            for item in audit.get("priority_actions", []):
                st.write(f"- {item}")

        with tab3:
            st.subheader("Copyable HTML")
            st.text_area("HTML", annotated_html, height=420)

            st.download_button(
                "⬇️ Download Annotated Audit HTML",
                data=annotated_html,
                file_name="geo_annotated_audit.html",
                mime="text/html",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Audit failed: {str(e)}")
