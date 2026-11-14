Code Debugger

A Python code debugger powered by RAG and a small local LLM. Paste buggy Python code and get a plain-language summary of the problem plus the corrected code. It runs fully on CPU: no GPU, no API key, no paid credits.

Screenshot

Features
Summary and corrected code for any pasted Python snippet
RAG over a PDF knowledge base of common Python errors (syntax, runtime and logic bugs), so fixes are guided by reference notes instead of guesses
Runs locally with a small Hugging Face model (Qwen2.5-Coder-1.5B-Instruct), no GPU needed
Streamlit interface with example snippets, a diff view of the changes, the retrieved reference notes, the raw model output, and session history
How it works
Your code
   |
   v
Retriever (Chroma + all-MiniLM-L6-v2 embeddings)  --> finds the most relevant entries in the PDF
   |
   v
Prompt (code + retrieved notes)
   |
   v
Local LLM (Qwen2.5-Coder-1.5B-Instruct via HuggingFacePipeline)
   |
   v
Summary + corrected code
The PDF is loaded with PyPDFLoader and split into one chunk per error entry using RecursiveCharacterTextSplitter.
Chunks are embedded with sentence-transformers/all-MiniLM-L6-v2 and stored in a Chroma vector store.
For each submitted snippet, the retriever returns the closest entries, which are added to the prompt.
The model replies in a fixed format (SUMMARY: and CORRECTED CODE:), and the app splits the reply into the two parts.
Tech stack

Python, LangChain, Hugging Face Transformers, Chroma, sentence-transformers, pypdf, Streamlit

Project structure
.
├── app.py                        # Streamlit frontend
├── code_debugger.py              # RAG pipeline and analyze_code()
├── python_debugging_guide.pdf    # Knowledge base
├── requirements.txt
├── .streamlit/config.toml        # Dark theme
└── README.md
Setup
bash
# 1. Clone
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
Run
bash
python -m streamlit run app.py

Open http://localhost:8501.

First run: the embedding model (~90 MB) and the LLM (~3 GB) are downloaded from Hugging Face once and cached. Loading takes a few minutes, and each answer takes a few seconds on CPU.

Use
Paste Python code into the editor, or click an example button.
Click Analyze code.
Read the result in the tabs: Summary, Corrected code, Changes, Reference notes, Raw output.
Customize the knowledge base

Replace or extend python_debugging_guide.pdf with your own notes. Keep each entry in the format N. Title followed by cause, fix, and examples, because the splitter cuts before each numbered title. After changing the PDF, delete the chroma_db folder so the vector store is rebuilt.

Limitations
A 1.5B model is small. It handles common errors well but can miss subtle logic bugs or ignore the reply format.
The corrected code is not executed or verified yet.
Retrieval quality depends on what the PDF covers.
Roadmap
[ ] Run the corrected code in a sandbox and retry if it still fails
[ ] LangGraph loop: analyze, fix, run, retry
[ ] Fallback to a second model when the first fails
[ ] Benchmark on a set of buggy snippets