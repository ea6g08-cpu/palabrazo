import streamlit as st
from openai import OpenAI


# -------------------------
# Helpers
# -------------------------
def parse_items(text: str):
    items = []
    seps = [" — ", " – ", " - ", "—", "–", "-"]

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("- "):
            line = line[2:].strip()
        else:
            if len(line) >= 3 and line[0].isdigit():
                if (line[1:3] == ". ") or (line[1:3] == ") "):
                    line = line[3:].strip()

        sep_found = None
        for sep in seps:
            if sep in line:
                sep_found = sep
                break
        if not sep_found:
            continue

        left, right = line.split(sep_found, 1)
        left = left.strip()
        right = right.strip()
        if not left or not right:
            continue

        items.append({"front": left, "back": right})

    return items


def norm_key(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def desired_count_for(kind: str) -> int:
    return 10 if kind == "Phrases" else 20


# -------------------------
# Page setup
# -------------------------
st.set_page_config(page_title="PalAbrazo", page_icon="🤗")
st.title("🤗 PalAbrazo")
st.caption("Generate vocabulary and practise with flashcards.")

tab_generate, tab_flashcards = st.tabs(["Generate", "Flashcards"])

# -------------------------
# Branding + UI foundation
# -------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    .block-container {
      padding-top: 2.25rem;
      padding-bottom: 2rem;
      max-width: 900px;
    }

    h1 { font-weight: 800 !important; letter-spacing: -0.5px; }
    h2, h3 { font-weight: 700 !important; letter-spacing: -0.2px; }

    div[data-testid="stTabs"] button {
      border-bottom: 2px solid transparent !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
      color: #ff70ae !important;
      font-weight: 700 !important;
      border-bottom: 3px solid #ff70ae !important;
    }
    div[data-testid="stTabs"] button::after {
      background: none !important;
    }

    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stBaseButton-primary"] button {
      background-color: #111111 !important;
      color: #ffffff !important;
      font-weight: 800 !important;
      border: none !important;
      border-radius: 12px !important;
      padding: 0.6rem 1.2rem !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stBaseButton-primary"] button:hover {
      background-color: #000000 !important;
      color: #ffffff !important;
    }

    div[data-testid="stButton"] button[kind="secondary"] {
      background-color: #ffffff !important;
      color: #111111 !important;
      border: 2px solid #111111 !important;
      font-weight: 700 !important;
      border-radius: 12px !important;
      padding: 0.55rem 1.1rem !important;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
      background-color: #111111 !important;
      color: #ffffff !important;
    }

    div[data-testid="stVerticalBlock"] { gap: 0.55rem; }
    p { margin-bottom: 0.25rem; }
    [data-testid="stMarkdownContainer"] p { margin-bottom: 0.15rem; }
    [data-testid="stCaptionContainer"] { margin-top: -0.2rem; }

    /* ===== Vocabulary list rows ===== */
    .pa-front {
        font-weight: 700;
        font-size: 16px;
        line-height: 1.3;
        word-break: break-word;
        display: block;
        margin: 0;
        padding: 0;
    }
    .pa-back {
        font-size: 14px;
        opacity: 0.55;
        line-height: 1.3;
        word-break: break-word;
        display: block;
        margin: 1px 0 0 0;
        padding: 0 0 8px 0;
    }

    div[data-testid="stHorizontalBlock"]:has(.pa-front) {
        border-bottom: 1px solid rgba(0,0,0,0.07);
        padding: 6px 0 !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.pa-front)
        > div[data-testid="stColumn"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.pa-front)
        > div[data-testid="stColumn"]:last-child {
        flex: 0 0 44px !important;
        min-width: 44px !important;
        width: 44px !important;
        padding: 0 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.pa-front)
        > div[data-testid="stColumn"]:last-child * {
        padding: 0 !important;
        margin: 0 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.pa-front)
        div[data-testid="stButton"] button {
        background: rgba(0,0,0,0.06) !important;
        border: none !important;
        box-shadow: none !important;
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 !important;
        font-size: 14px !important;
        font-weight: 900 !important;
        color: rgba(0,0,0,0.5) !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.pa-front)
        div[data-testid="stButton"] button:hover {
        background: rgba(0,0,0,0.15) !important;
        color: rgba(0,0,0,0.9) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Session state
# -------------------------
if "items" not in st.session_state:
    st.session_state["items"] = []
if "meta" not in st.session_state:
    st.session_state["meta"] = {}
if "removed" not in st.session_state:
    st.session_state["removed"] = set()
if "card_index" not in st.session_state:
    st.session_state["card_index"] = 0
if "show_back" not in st.session_state:
    st.session_state["show_back"] = False
if "direction" not in st.session_state:
    st.session_state["direction"] = "target_first"

# -------------------------
# OpenAI
# -------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_RULES = """
You are an expert language teacher and CEFR examiner with deep knowledge of
vocabulary acquisition.

Your task: generate exactly {count} {kind} in {language} for a learner who
wants to communicate confidently in real situations involving: {topic}

CEFR LEVEL: {level}
Use this definition strictly:

A1 — Very high-frequency words. Basic, concrete, essential survival vocabulary.
     Example register: a tourist on their first day abroad.

A2 — Common everyday words. Simple but slightly more varied than A1.
     Avoid any word already typical at A1.

B1 — Topic-specific intermediate words. Less common than A2 but not technical.
     A learner could encounter these in a newspaper or casual conversation.
     Avoid any word typical at A1 or A2.

B2 — Moderately advanced, topic-specific. Words an educated native speaker
     uses naturally in this context. Not found in a beginner list.
     Avoid any word typical at A1, A2, or B1.

C1 — Low-frequency, precise, or nuanced vocabulary. Register-aware.
     Words that distinguish a fluent speaker from an intermediate one.
     Avoid anything typical below C1.

C2 — Rare, highly nuanced, or domain-specific. Native-level sophistication.
     Words that even educated non-native speakers rarely know.
     Avoid anything typical below C2.

QUALITY RULES:
- Choose words a native speaker would genuinely use in this specific situation
- Prefer vocabulary that is DISTINCTIVE to this topic and this level
- Do NOT choose the most obvious or generic words for the topic
- Each word must feel meaningfully different in difficulty from the others

SELF-CHECK:
Before outputting, silently verify: would each item appear on a {level}
vocabulary list — and NOT on a list one level below? If not, replace it.

FORMAT RULES — follow exactly:
- Output ONLY {count} lines. No intro, no commentary, no blank lines.
- Every line: - <{language} word> — <English translation>
- Separator is exactly " — " (space, em dash, space). Nothing else.
- Do NOT use numbering like "1." or "1)".
"""

# -------------------------
# Generate tab
# -------------------------
with tab_generate:
    with st.form("generate_form"):
        c1, c2, c3 = st.columns(3)

        with c1:
            kind = st.selectbox("Generate", ["Words", "Verbs", "Phrases"])
        with c2:
            language = st.selectbox("Language", ["Spanish", "French", "Italian", "German", "Catalan"])
        with c3:
            level = st.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"], index=2)

        topic = st.text_input("Topic", placeholder="e.g. Rock climbing")
        submit = st.form_submit_button("Generate")

    if submit and topic.strip():
        count = desired_count_for(kind)
        rules = SYSTEM_RULES.format(count=count, language=language, level=level, kind=kind, topic=topic)

        with st.spinner("Generating..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": rules},
                        {"role": "user", "content": topic},
                    ],
                    temperature=0.7,
                    max_tokens=800,
                )
            except Exception as e:
                st.error(f"OpenAI request failed: {e}")
                st.stop()

        raw = response.choices[0].message.content or ""
        items = parse_items(raw)

        if not items:
            st.warning("No items parsed. Showing raw model output below (for debugging).")
            st.code(raw)

        st.session_state["items"] = items
        st.session_state["meta"] = {"kind": kind, "language": language, "level": level, "topic": topic}
        st.session_state["removed"] = set()
        st.session_state["card_index"] = 0
        st.session_state["show_back"] = False

    items = st.session_state["items"]

    if not items:
        st.info("Generate a list to see results.")
    else:
        desired = desired_count_for(st.session_state["meta"]["kind"])
        missing = max(0, desired - len(items))

        if st.button(f"Top up ({missing})", disabled=missing == 0, type="secondary"):
            existing = {norm_key(i["front"]) for i in items}
            excluded = existing | st.session_state["removed"]

            meta = st.session_state["meta"]
            rules = SYSTEM_RULES.format(
                count=missing,
                language=meta["language"],
                level=meta["level"],
                kind=meta["kind"],
                topic=meta["topic"],
            )

            guard = ""
            if excluded:
                guard = "\nNever include these words — they have already been generated:\n" + "\n".join(f"- {k}" for k in excluded)

            with st.spinner("Topping up..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": rules + guard},
                        {"role": "user", "content": meta["topic"]},
                    ],
                    temperature=0.7,
                    max_tokens=800,
                )

            new_items = parse_items(response.choices[0].message.content or "")
            merged = list(items)
            seen = {norm_key(i["front"]) for i in merged}

            for it in new_items:
                k = norm_key(it["front"])
                if k and k not in seen and k not in st.session_state["removed"]:
                    merged.append(it)
                    seen.add(k)

            st.session_state["items"] = merged[:desired]
            st.rerun()

        st.divider()
        st.write("Tap ✕ to remove items you already know.")

        for i, it in enumerate(st.session_state["items"]):
            col_word, col_btn = st.columns([0.88, 0.12])

            with col_word:
                st.markdown(
                    f'<span class="pa-front">{it["front"]}</span>'
                    f'<span class="pa-back">{it["back"]}</span>',
                    unsafe_allow_html=True,
                )

            with col_btn:
                if st.button("✕", key=f"rm_{i}"):
                    st.session_state["removed"].add(norm_key(it["front"]))
                    st.session_state["items"].pop(i)
                    st.session_state["card_index"] = 0
                    st.session_state["show_back"] = False
                    st.rerun()

# -------------------------
# Flashcards tab
# -------------------------
with tab_flashcards:
    items = st.session_state["items"]

    if not items:
        st.info("Generate a list first.")
    else:
        total = len(items)
        idx = st.session_state["card_index"]
        card = items[idx]

        direction = st.radio(
            "Direction",
            ["Target → English", "English → Target"],
            horizontal=True,
            index=0 if st.session_state["direction"] == "target_first" else 1,
        )
        st.session_state["direction"] = (
            "target_first" if direction == "Target → English" else "english_first"
        )

        if st.session_state["direction"] == "target_first":
            front, back = card["front"], card["back"]
        else:
            front, back = card["back"], card["front"]

        text = back if st.session_state["show_back"] else front

        if st.button(text, use_container_width=True):
            st.session_state["show_back"] = not st.session_state["show_back"]
            st.rerun()

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("⬅️"):
                st.session_state["card_index"] = (idx - 1) % total
                st.session_state["show_back"] = False
                st.rerun()

        with c2:
            if st.button("🔄"):
                st.session_state["show_back"] = not st.session_state["show_back"]
                st.rerun()

        with c3:
            if st.button("➡️"):
                st.session_state["card_index"] = (idx + 1) % total
                st.session_state["show_back"] = False
                st.rerun()