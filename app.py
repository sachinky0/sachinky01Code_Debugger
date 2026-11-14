import time
import difflib
import streamlit as st
from code_debugger import analyze_code   # your backend (returns summary, fixed_code, notes_used, raw)

# ---------- Page setup ----------
st.set_page_config(page_title="Code Debugger", page_icon="🐞", layout="wide")  # wide = uses full screen

# ---------- Custom CSS (small touches only) ----------
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}              /* hide default menu and footer */
.hero {font-size: 2.4rem; font-weight: 800;          /* big gradient title */
       background: linear-gradient(90deg, #7C5CFF, #00D4FF);
       -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
.sub {color: #8B93A7; margin-top: -8px; margin-bottom: 18px;}
.stButton > button {border-radius: 10px; font-weight: 600;}   /* rounded buttons */
</style>
""", unsafe_allow_html=True)   # unsafe_allow_html lets Streamlit render the HTML above

# ---------- Session state: values that survive reruns ----------
# Streamlit reruns the script on every click, so we store data here.
st.session_state.setdefault("result", None)   # latest analysis
st.session_state.setdefault("history", [])    # past analyses
st.session_state.setdefault("code_input", "") # text inside the editor

# ---------- Example snippets ----------
EXAMPLES = {
    "Syntax": "print('hi'",
    "Zero division": "x = 10 / 0",
    "Name error": "print(total)",
    "Logic bug": "def add(x, items=[]):\n    items.append(x)\n    return items",
}

def load_example(text):
    st.session_state.code_input = text   # callback: fills the editor before the rerun

def clear_history():
    st.session_state.history = []
    st.session_state.result = None

# ---------- Sidebar ----------
with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. Your code is matched against a **PDF knowledge base** (RAG)\n"
        "2. A local **Qwen2.5-Coder** model reads the code and the notes\n"
        "3. You get a **summary** and the **corrected code**"
    )
    st.divider()
    st.subheader("History")
    if not st.session_state.history:
        st.caption("No analyses yet.")
    for i, item in enumerate(st.session_state.history[:5]):   # show the last 5
        first_line = item["code"].splitlines()[0][:28] if item["code"].strip() else "code"
        with st.expander(f"{i + 1}. {first_line}"):
            st.code(item["fixed_code"] or "No fix returned", language="python")
    st.button("Clear history", on_click=clear_history, use_container_width=True)

# ---------- Header ----------
st.markdown('<div class="hero">Code Debugger</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Paste Python code. Get a clear summary and the corrected version.</div>',
            unsafe_allow_html=True)

# ---------- Two-column layout: input left, results right ----------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Your code")

    # One button per example, side by side
    cols = st.columns(len(EXAMPLES))
    for col, (name, snippet) in zip(cols, EXAMPLES.items()):
        col.button(name, key=f"ex_{name}", on_click=load_example, args=(snippet,),
                   use_container_width=True)

    code = st.text_area(
        "code", key="code_input", height=320,          # key links it to session_state.code_input
        label_visibility="collapsed",                  # hide the label, the subheader says it
        placeholder="# Paste your Python code here...",
    )
    analyze = st.button("Analyze code", type="primary", use_container_width=True)

# ---------- Run the analysis ----------
if analyze:
    if not code.strip():
        left.warning("Please paste some code first.")
    else:
        try:
            with st.spinner("Analyzing... the first run can take a while on CPU"):
                start = time.perf_counter()
                result = analyze_code(code)                    # your backend call
                result["seconds"] = time.perf_counter() - start
                result["code"] = code                          # keep the original for the diff
            st.session_state.result = result
            st.session_state.history.insert(0, result)         # newest first
        except Exception as e:
            left.error(f"Analysis failed: {e}")

# ---------- Show results ----------
with right:
    st.subheader("Result")
    res = st.session_state.result

    if res is None:
        st.info("Results will appear here after you click **Analyze code**.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Status", "Fixed" if res["fixed_code"] else "No fix")
        m2.metric("Time", f"{res['seconds']:.1f}s")
        m3.metric("Lines", len(res["code"].splitlines()))

        tab_sum, tab_fix, tab_diff, tab_notes, tab_raw = st.tabs(
            ["Summary", "Corrected code", "Changes", "Reference notes", "Raw output"]
        )

        with tab_sum:
            st.write(res["summary"] or "The model returned no summary. Check the Raw output tab.")

        with tab_fix:
            if res["fixed_code"]:
                st.code(res["fixed_code"], language="python")   # has a built-in copy button
                st.download_button("Download fixed code", res["fixed_code"],
                                   file_name="fixed_code.py")
            else:
                st.warning("No corrected code was returned. Check the Raw output tab.")

        with tab_diff:
            # unified_diff compares line by line: lines with - were removed, + were added
            diff = "\n".join(difflib.unified_diff(
                res["code"].splitlines(), res["fixed_code"].splitlines(),
                fromfile="original", tofile="fixed", lineterm="",
            ))
            st.code(diff or "No changes.", language="diff")

        with tab_notes:
            st.caption("Entries retrieved from the PDF (this is the RAG part)")
            st.text(res["notes_used"])

        with tab_raw:
            st.text(res["raw"])   # untouched model reply, useful for debugging the prompt