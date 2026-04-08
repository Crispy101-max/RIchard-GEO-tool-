import streamlit as st
from geo_shared import ensure_geo_context, get_client, call_gemini_json

geo = ensure_geo_context()

st.set_page_config(page_title="Entity Extraction", page_icon="🧠", layout="wide")
st.title("🧠 Entity Extraction")
st.write(
    "Identify the entities and relationships required to support the target AI prompts."
)

st.subheader("🎯 Target AI Prompts")
for p in geo.get("target_prompts", []):
    st.write(f"- {p}")

run = st.button("Run / Refresh Entity Extraction", type="primary", use_container_width=True)

if run or not geo.get("entities"):
    client = get_client()

    SYSTEM_PROMPT = """
You are a senior entity modeling and knowledge graph specialist.

Extract and evaluate:
- primary entities
- secondary entities
- supporting entities
- missing or weak entities
- relationship gaps

Optimise for Generative Engine Optimisation.

Return JSON ONLY in this structure:
{
  "summary": "",
  "primary_entities": [],
  "secondary_entities": [],
  "supporting_entities": [],
  "entity_clarity_assessment": {
    "overall_clarity": "",
    "issues": []
  },
  "missing_or_weak_entities": [],
  "entity_relationship_gaps": [],
  "knowledge_graph_readiness": "",
  "priority_entity_actions": []
}
"""

    source_text = geo.get("rewritten_content") or geo["page_snapshot"]["page_text"]

    USER_PROMPT = f"""
COMPANY:
{geo["company"]}

TARGET PROMPTS:
{geo.get("target_prompts", [])}

AUDIT:
{geo.get("audit", {})}

SOURCE TEXT:
{source_text}
"""

    with st.spinner("Extracting entities..."):
        geo["entities"] = call_gemini_json(client, SYSTEM_PROMPT, USER_PROMPT)
        st.session_state.geo_context = geo

entities = geo.get("entities", {})

if entities:
    st.subheader("🧠 Summary")
    st.write(entities.get("summary", ""))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🎯 Primary Entities")
        for item in entities.get("primary_entities", []):
            st.write(f"- {item}")

    with col2:
        st.subheader("🧩 Secondary Entities")
        for item in entities.get("secondary_entities", []):
            st.write(f"- {item}")

    with col3:
        st.subheader("📎 Supporting Entities")
        for item in entities.get("supporting_entities", []):
            st.write(f"- {item}")

    st.subheader("🔍 Entity Clarity")
    clarity = entities.get("entity_clarity_assessment", {})
    st.write(clarity.get("overall_clarity", ""))
    for item in clarity.get("issues", []):
        st.write(f"- {item}")

    st.subheader("❗ Missing / Weak Entities")
    for item in entities.get("missing_or_weak_entities", []):
        st.write(f"- {item}")

    st.subheader("🔗 Relationship Gaps")
    for item in entities.get("entity_relationship_gaps", []):
        st.write(f"- {item}")

    st.subheader("🕸 Knowledge Graph Readiness")
    st.write(entities.get("knowledge_graph_readiness", ""))

    st.subheader("✅ Priority Entity Actions")
    for item in entities.get("priority_entity_actions", []):
        st.write(f"- {item}")
``
