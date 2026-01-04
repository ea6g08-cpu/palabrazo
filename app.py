import streamlit as st
from openai import OpenAI


def parse_items(text: str):
    """
    Converts model output lines like:
    - <target> — <english>
    into a list of dicts: [{"front": "...", "back": "..."}, ...]
    """
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        line = line[2:]  # remove "- "
        if " — " not in line:
            continue
        left, right = line.split(" — ", 1)
        items.append({"front": left.strip(), "back": right.strip()})
    return items


st.set_page_config(page_title="PalAbrazo", page_icon="🤗")

st.title("🤗 PalAbrazo")
st.caption(
    "A word hug for language learners — generate words/verbs/phrases with English meanings, then practise with flashcards."
)

tab_generate, tab_flashcards = st.tabs(["Generate", "Flashcards"])

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_RULES_TEMPLATE = """
You are a language teacher. Generate exactly {item_count} items about the user's topic.

Target language: {target_language}
CEFR level: {cefr_level}
Generation type: {generate_type}

CEFR guidance:
- A1/A2: very common, concrete, high-frequency language.
- B1: practical everyday language.
- B2: more precise language; some abstraction.
- C1/C2: advanced, nuanced language appropriate to the topic.

STRICT output format:
- Output ONLY {item_count} lines (no intro, no headings).
- Each line MUST start with "- " (dash + space).
- Each line MUST be: - <target language> — <English>
- Use " — " exactly (space em-dash space). No extra text.
- If you cannot follow the type rules, regenerate internally until you can.

Type rules (apply ONLY the matching section):

[WORDS]
- Output single-word items only (one token/word, or an article + single noun).
- Allowed formats:
  - Noun: article + singular noun (e.g., "el libro", "la casa"). No multi-word nouns.
  - Verb/adjective/adverb: single word only. No article.
- NOT allowed: phrases, collocations, multi-word items, sentences, punctuation.

[VERBS]
- Output infinitive verbs only, single word (e.g., "hablar", "comer").
- NOT allowed: any nouns, any sentences, any multi-word items.

[PHRASES]
- Output complete, useful sentences a learner would actually say (8–14 words).
- Each item MUST contain a verb and end with punctuation (., ?, !).
- NOT allowed: single words, noun-only entries.

Quality rules:
- Avoid English loanwords unless they are the most common term in the target language.
- Keep items relevant to the topic and appropriate to the CEFR level.
"""


# -------------------------
# Generate tab
# -------------------------
with tab_generate:
    with st.form("vocab_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            generate_type = st.selectbox("Generate", ["Words", "Verbs", "Phrases"], index=0)

        with col2:
            target_language = st.selectbox(
                "Language",
                ["Spanish", "French", "Italian", "German", "Catalan"],
                index=0,
            )

        with col3:
            cefr_level = st.selectbox(
                "Level",
                ["A1", "A2", "B1", "B2", "C1", "C2"],
                index=2,  # default B1
            )

        user_input = st.text_input(
            "Topic or sentence",
            placeholder="e.g., Rock climbing",
        )

        generate = st.form_submit_button("Generate")

    if generate:
        if not user_input.strip():
            st.warning("Please enter a topic or sentence first.")
        else:
            item_count = 10 if generate_type == "Phrases" else 20
            max_tokens = 650 if generate_type == "Phrases" else 450

            system_rules = SYSTEM_RULES_TEMPLATE.format(
                target_language=target_language,
                cefr_level=cefr_level,
                generate_type=generate_type,
                item_count=item_count,
            )

            with st.spinner("Generating..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_rules},
                        {"role": "user", "content": user_input},
                    ],
                    temperature=0.6,
                    max_tokens=max_tokens,
                )

            label_map = {
                "Words": "Your word list",
                "Verbs": "Your verb list",
                "Phrases": "Your phrase list",
            }

            st.subheader(label_map.get(generate_type, "Your list"))

            raw_text = response.choices[0].message.content.strip()
            st.text(raw_text)

            st.session_state["last_items"] = parse_items(raw_text)
            st.session_state["last_meta"] = {
                "generate_type": generate_type,
                "target_language": target_language,
                "cefr_level": cefr_level,
                "topic": user_input,
            }

            # Reset flashcard position when generating a new list
            st.session_state["card_index"] = 0
            st.session_state["show_back"] = False


# -------------------------
# Flashcards tab
# -------------------------
with tab_flashcards:
    st.subheader("Flashcards")

    items = st.session_state.get("last_items", [])
    meta = st.session_state.get("last_meta", {})

    if not items:
        st.info("Generate a list first, then come back here to practise with flashcards.")
    else:
        total = len(items)

        # Ensure flashcard state exists
        if "card_index" not in st.session_state:
            st.session_state["card_index"] = 0
        if "show_back" not in st.session_state:
            st.session_state["show_back"] = False

        # Keep index in range if list length changes
        if st.session_state["card_index"] >= total:
            st.session_state["card_index"] = 0

        st.caption(
            f'{meta.get("target_language", "")} • {meta.get("cefr_level", "")} • {meta.get("generate_type", "")}'
        )
        st.write(f"Card: **{st.session_state['card_index'] + 1} / {total}**")

        idx = st.session_state["card_index"]
        card = items[idx]

        # Flashcard styling (colour depends on side)
        if st.session_state["show_back"]:
            # English side → blue
            st.markdown(
                """
                <style>
                div[data-testid="stButton"] > button[kind="primary"] {
                    background-color: #2563eb !important; /* blue */
                    color: white !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Target language side → green
            st.markdown(
                """
                <style>
                div[data-testid="stButton"] > button[kind="primary"] {
                    background-color: #16a34a !important; /* green */
                    color: white !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )



        card_text = card["back"] if st.session_state["show_back"] else card["front"]
        card_label = "English" if st.session_state["show_back"] else "Target language"

        # Click the card to flip
        st.markdown('<div class="flashcard">', unsafe_allow_html=True)
        if st.button(card_text, key="fc_card", type="primary", use_container_width=True):
            st.session_state["show_back"] = not st.session_state["show_back"]
            st.rerun()


        st.markdown("</div>", unsafe_allow_html=True)

        st.caption(card_label)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("⬅️ Previous", key="fc_prev", type="secondary"):
                st.session_state["card_index"] = (idx - 1) % total
                st.session_state["show_back"] = False
                st.rerun()

        with col2:
            if st.button("🔄 Flip", key="fc_flip", type="secondary"):
                st.session_state["show_back"] = not st.session_state["show_back"]
                st.rerun()

        with col3:
            if st.button("Next ➡️", key="fc_next", type="secondary"):
                st.session_state["card_index"] = (idx + 1) % total
                st.session_state["show_back"] = False
                st.rerun()

