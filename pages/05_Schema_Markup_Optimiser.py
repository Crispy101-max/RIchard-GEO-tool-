import json
import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(page_title="Schema Markup Optimiser", page_icon="🧩", layout="wide")
st.title("🧩 Schema Markup Optimiser")
st.write(
    "Generate or improve JSON‑LD so the page meaning is encoded cleanly for AI systems and search engines."
)

st.subheader("🎯 Target AI Prompts")
for p in geo.get("target_prompts", []):
    st.write(f"- {p}")

run = st.button("Run / Refresh Schema Optimiser", type="primary", use_container_width=True)

if run or not geo.get("schema"):
    client = get_client()

    SYSTEM_PROMPT = """
You are a structured data architect.

Create clean, conservative JSON-LD aligned to:
- the page content
- the target prompts
- the extracted entities
- the business context

Use only facts visible in the source content or provided in the business context.
Do NOT invent ratings, prices, or unsupported claims.

Return JSON ONLY in this structure:
{
  "summary": "",
  "recommended_schema_types": [],
  "schema_jsonld": {},
  "notes": []
}
"""

    source_content = geo.get("rewritten_content") or geo["page_snapshot"]["page_text"]

    USER_PROMPT = f"""
COMPANY:
{geo["company"]}

TARGET PROMPTS:
{geo.get("target_prompts", [])}

ENTITIES:
{geo.get("entities", {})}

EXISTING JSON-LD:
{geo["page_snapshot"].get("existing_jsonld", [])}

SOURCE CONTENT:
{source_content}
"""

    with st.spinner("Optimising schema..."):
        geo["schema"] = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)
        st.session_state.geo_context = geo

schema = geo.get("schema", {})

if schema:
    st.subheader("🧠 Summary")
    st.write(schema.get("summary", ""))

    st.subheader("Recommended schema types")
    for item in schema.get("recommended_schema_types", []):
        st.write(f"- {item}")

    st.subheader("✅ JSON-LD")
    st.code(json.dumps(schema.get("schema_jsonld", {}), indent=2, ensure_ascii=False), language="json")

    st.subheader("Notes")
    for item in schema.get("notes", []):
        st.write(f"- {item}")
