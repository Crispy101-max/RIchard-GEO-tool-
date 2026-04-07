import os
import json
import re
from typing import Any, Dict, Optional

import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Schema Markup Strategist",
    page_icon="🧩",
    layout="wide"
)

# ============================================================
# API KEY / CLIENT
# ============================================================
def get_api_key() -> str:
    try:
        if "API_Key" in st.secrets:
            return st.secrets["API_Key"]
    except Exception:
        pass

    return os.getenv("API_Key") or os.getenv("GEMINI_API_KEY") or ""


API_KEY = get_api_key()

if not API_KEY:
    st.error("No Gemini API key found. Add it to Streamlit secrets as `API_Key`.")
    st.stop()

client = genai.Client(api_key=API_KEY)


# ============================================================
# MODEL CONFIG
# ============================================================
MODEL_NAME = "gemini-2.5-pro"

# Low-variance config for structured output
GEN_CONFIG_JSON = types.GenerateContentConfig(
    temperature=0,
    top_p=0.1,
    top_k=1,
    candidate_count=1,
    max_output_tokens=8192,
    seed=42,
    response_mime_type="application/json",
)


# ============================================================
# UTILS
# ============================================================
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def safe_json_parse(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start:end + 1]
        return json.loads(snippet)

    raise ValueError("Could not parse JSON from model output.")


@st.cache_data(show_spinner=False)
def scrape_page(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag.get("content", "").strip()

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = clean_whitespace(tag.get_text(" ", strip=True))
        if txt:
            headings.append(txt)

    existing_jsonld = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        txt = script.get_text(strip=True)
        if txt:
            existing_jsonld.append(txt)

    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    page_text = clean_whitespace(soup.get_text(separator=" ", strip=True))
    page_text = page_text[:30000]

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings[:25],
        "page_text": page_text,
        "existing_jsonld": existing_jsonld[:10],
    }


def call_gemini_json(user_text: str, system_instruction: str) -> Dict[str, Any]:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_text,
        config=types.GenerateContentConfig(
            temperature=GEN_CONFIG_JSON.temperature,
            top_p=GEN_CONFIG_JSON.top_p,
            top_k=GEN_CONFIG_JSON.top_k,
            candidate_count=GEN_CONFIG_JSON.candidate_count,
            max_output_tokens=GEN_CONFIG_JSON.max_output_tokens,
            seed=GEN_CONFIG_JSON.seed,
            response_mime_type=GEN_CONFIG_JSON.response_mime_type,
            system_instruction=system_instruction,
        ),
    )
    return safe_json_parse(response.text)


# ============================================================
# SYSTEM PROMPT
# ============================================================
SCHEMA_SYSTEM_PROMPT = """
You are a senior structured data strategist, technical SEO architect, and entity-modelling specialist.

Your job is to generate highly useful schema markup recommendations and JSON-LD for real business websites.

CORE PRINCIPLES:
1. Use Schema.org vocabulary.
2. Prefer JSON-LD.
3. The schema must match the visible content of the page.
4. Never invent facts that are not visible on the page or explicitly supplied by the user.
5. If strategic information is supplied by the user (target audience, niche, differentiators, positioning, etc.)
   but is NOT clearly visible on the page, DO NOT silently insert it as if it were already published.
   Instead:
   - mention it under `content_sync_notes`
   - mention whether it should be added on-page before being added to schema
   - only encode it if it cleanly maps to a schema property AND can be justified by the provided inputs
6. Google-rich-result-focused schema takes priority over vague or decorative schema.
7. Always think in two layers:
   A. UNIVERSAL / STABLE LAYER:
      - Organization or LocalBusiness
      - WebPage
      - BreadcrumbList when hierarchy is present
   B. PAGE-SPECIFIC LAYER:
      - Product + Offer for product pages
      - Article / BlogPosting / NewsArticle for editorial pages
      - LocalBusiness for physical-location businesses
      - Service-oriented recommendation where page is a service page, but do not force unsupported rich-result markup
8. Product pages should not be treated like category pages.
9. Category/listing pages are not single-product rich-result pages.
10. Output must be commercially useful, implementation-ready, and conservative.

WHAT TO OPTIMISE FOR:
- explicit business identity
- explicit page type
- explicit product/service meaning
- machine-readable commercial facts
- page hierarchy
- trust / clarity / entity consistency
- strong alignment between schema and visible page content

IMPORTANT BUSINESS STRATEGY FIELDS:
When the user provides business strategy context, evaluate whether and how it can influence schema:
- target audience
- what the business is trying to achieve
- what problem it solves
- who it serves
- purpose / mission
- differentiators
- niche / category
- market served
- offer / product focus

Use that information to:
- choose better schema types
- improve descriptions / classification
- identify missing on-page content
- recommend what should be added to the site before markup is finalised

DO NOT:
- invent ratings, prices, SKUs, certifications, opening hours, shipping, return policies, or authors
- stuff marketing copy into schema unnaturally
- generate unsupported or misleading fields
- treat hidden strategy notes as already published website facts unless the user explicitly wants a future-state draft and you clearly label it as such

REQUIRED OUTPUT FORMAT:
Return valid JSON only in exactly this structure:

{
  "page_classification": {
    "page_type": "",
    "primary_schema_type": "",
    "secondary_schema_types": []
  },
  "strategy_summary": {
    "business_identity": "",
    "target_audience": "",
    "business_goal": "",
    "offer_summary": "",
    "differentiators": "",
    "niche": "",
    "who_they_serve": "",
    "purpose": ""
  },
  "universal_schema_layer": {
    "should_use_organization_or_localbusiness": "",
    "should_use_webpage": true,
    "should_use_breadcrumbs": true,
    "notes": []
  },
  "tailored_schema_layer": {
    "tailored_fields_to_focus_on": [],
    "why_these_fields_matter": []
  },
  "current_schema_issues": [],
  "missing_data": [],
  "content_sync_notes": [],
  "implementation_notes": [],
  "schema_jsonld": {}
}

OUTPUT RULES:
- `page_classification.page_type` should be one of:
  homepage, product_page, article_page, local_business_page, service_page,
  category_page, about_page, contact_page, other
- `should_use_organization_or_localbusiness` must be one of:
  Organization, LocalBusiness, MoreSpecificLocalBusinessSubtype, Neither
- `schema_jsonld` should be either:
  - a single object, or
  - an @graph object
- prefer @graph when multiple entities are useful
- if a field is unknown, either omit it from schema_jsonld OR use [DATA NEEDED: ...] inside notes lists
- never put fake placeholders into price, rating, or regulated business facts unless clearly marked in notes instead of schema
"""


# ============================================================
# UI
# ============================================================
st.title("🧩 Schema Markup Strategist")
st.write(
    "This tool creates a detailed, strategy-aware schema recommendation. "
    "It combines a standard schema skeleton with AI-tailored fields for the specific business, page, offer, and audience."
)

st.markdown("### 1) Input source")
input_mode = st.radio(
    "Choose input type",
    ["Website URL", "Paste page content manually"],
    horizontal=True
)

page_data: Optional[Dict[str, Any]] = None

if input_mode == "Website URL":
    url = st.text_input(
        "Paste a page URL",
        placeholder="https://example.com/product-page"
    )
else:
    pasted_title = st.text_input("Page title")
    pasted_meta = st.text_input("Meta description")
    pasted_headings = st.text_area("Headings (one per line)", height=120)
    pasted_content = st.text_area("Visible page content", height=260)
    pasted_existing_schema = st.text_area(
        "Existing JSON-LD on the page (optional)",
        height=180
    )

st.markdown("### 2) Client strategy inputs")
col1, col2 = st.columns(2)

with col1:
    business_name = st.text_input("Business / brand name")
    business_type = st.text_input("Business type", placeholder="Skincare ecommerce brand, local dentist, SaaS, etc.")
    target_audience = st.text_area("Target audience", height=90, placeholder="Who are they trying to serve?")
    business_goal = st.text_area("Primary business goal", height=90, placeholder="What are they trying to achieve?")
    niche = st.text_input("Niche / market")
    differentiators = st.text_area("Differentiators", height=90, placeholder="What makes them different?")

with col2:
    offer_summary = st.text_area("Product / service summary", height=90, placeholder="What do they sell or provide?")
    who_they_serve = st.text_area("Who they serve", height=90)
    purpose = st.text_area("Purpose / mission", height=90)
    service_area = st.text_input("Service area / geography")
    desired_page_type = st.selectbox(
        "If you already know the page type, choose it (optional)",
        [
            "",
            "homepage",
            "product_page",
            "article_page",
            "local_business_page",
            "service_page",
            "category_page",
            "about_page",
            "contact_page",
            "other"
        ]
    )

run = st.button("Generate Schema Strategy", type="primary", use_container_width=True)


# ============================================================
# MAIN LOGIC
# ============================================================
if run:
    try:
        if input_mode == "Website URL":
            if not url.strip().startswith("http"):
                st.error("Please enter a valid URL starting with http or https.")
                st.stop()

            with st.spinner("Scraping page..."):
                page_data = scrape_page(url)
        else:
            if not pasted_content.strip():
                st.error("Please paste the page content.")
                st.stop()

            page_data = {
                "url": "",
                "title": pasted_title.strip(),
                "meta_description": pasted_meta.strip(),
                "headings": [h.strip() for h in pasted_headings.splitlines() if h.strip()],
                "page_text": clean_whitespace(pasted_content)[:30000],
                "existing_jsonld": [pasted_existing_schema.strip()] if pasted_existing_schema.strip() else [],
            }

        strategy_block = {
            "business_name": business_name.strip(),
            "business_type": business_type.strip(),
            "target_audience": target_audience.strip(),
            "business_goal": business_goal.strip(),
            "niche": niche.strip(),
            "differentiators": differentiators.strip(),
            "offer_summary": offer_summary.strip(),
            "who_they_serve": who_they_serve.strip(),
            "purpose": purpose.strip(),
            "service_area": service_area.strip(),
            "desired_page_type": desired_page_type.strip(),
        }

        user_prompt = f"""
PAGE DATA
=========
URL:
{page_data["url"]}

TITLE:
{page_data["title"]}

META DESCRIPTION:
{page_data["meta_description"]}

HEADINGS:
{json.dumps(page_data["headings"], ensure_ascii=False)}

VISIBLE PAGE CONTENT:
{page_data["page_text"]}

EXISTING JSON-LD:
{json.dumps(page_data["existing_jsonld"], ensure_ascii=False)}

CLIENT STRATEGY INPUTS
======================
{json.dumps(strategy_block, ensure_ascii=False, indent=2)}

TASK
====
1. Classify the page.
2. Decide the best schema architecture using:
   - universal/stable schema layer
   - tailored/client-specific schema layer
3. Explain what can be standardised across clients vs what must be tailored here.
4. Generate implementation-ready JSON-LD.
5. If strategy inputs are not visible on the page, explain that under content_sync_notes instead of pretending they already exist on-page.
6. Make the output commercially useful and detailed.
"""

        with st.spinner("Generating schema strategy..."):
            result = call_gemini_json(user_prompt, SCHEMA_SYSTEM_PROMPT)

        st.success("Schema strategy generated.")

        classification = result.get("page_classification", {})
        strategy_summary = result.get("strategy_summary", {})
        universal_schema_layer = result.get("universal_schema_layer", {})
        tailored_schema_layer = result.get("tailored_schema_layer", {})
        current_schema_issues = result.get("current_schema_issues", [])
        missing_data = result.get("missing_data", [])
        content_sync_notes = result.get("content_sync_notes", [])
        implementation_notes = result.get("implementation_notes", [])
        schema_jsonld = result.get("schema_jsonld", {})

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "📌 Classification",
                "🎯 Strategy Summary",
                "🧱 Universal vs Tailored",
                "🧩 Final JSON-LD",
                "⚠️ Missing Data / Sync Notes",
                "🔍 Source Data"
            ]
        )

        with tab1:
            st.subheader("Page Classification")
            st.json(classification)

            st.subheader("Current Schema Issues")
            if current_schema_issues:
                for item in current_schema_issues:
                    st.write(f"- {item}")
            else:
                st.write("No current schema issues returned.")

        with tab2:
            st.subheader("Business / Strategy Summary")
            st.json(strategy_summary)

        with tab3:
            st.subheader("Universal Schema Layer")
            st.json(universal_schema_layer)

            st.subheader("Tailored Schema Layer")
            st.json(tailored_schema_layer)

        with tab4:
            st.subheader("Final JSON-LD")
            schema_pretty = json.dumps(schema_jsonld, indent=2, ensure_ascii=False)
            st.code(schema_pretty, language="json")

            st.download_button(
                label="⬇️ Download JSON-LD",
                data=schema_pretty,
                file_name="schema_strategy_output.json",
                mime="application/json",
                use_container_width=True
            )

            st.subheader("Implementation Notes")
            if implementation_notes:
                for item in implementation_notes:
                    st.write(f"- {item}")
            else:
                st.write("No implementation notes returned.")

        with tab5:
            st.subheader("Missing Data")
            if missing_data:
                for item in missing_data:
                    st.write(f"- {item}")
            else:
                st.write("No missing data returned.")

            st.subheader("Content Sync Notes")
            if content_sync_notes:
                for item in content_sync_notes:
                    st.write(f"- {item}")
            else:
                st.write("No content sync notes returned.")

        with tab6:
            st.subheader("Source Data Used")
            st.write("**URL:**", page_data["url"])
            st.write("**Title:**", page_data["title"])
            st.write("**Meta description:**", page_data["meta_description"])
            st.write("**Headings:**", page_data["headings"])
            st.text_area("Visible page text", page_data["page_text"], height=260)
            st.text_area(
                "Existing JSON-LD found",
                "\n\n".join(page_data["existing_jsonld"]) if page_data["existing_jsonld"] else "",
                height=180
            )

    except Exception as e:
        st.error(f"Error: {str(e)}")

