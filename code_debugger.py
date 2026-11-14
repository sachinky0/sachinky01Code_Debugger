from langchain_huggingface import ChatHuggingFace,HuggingFacePipeline,HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
load_dotenv()

pdf=PyPDFLoader("python_debugging_guide.pdf")
data=pdf.load()

splitter = RecursiveCharacterTextSplitter(
    separators=[r"\n(?=\d+\. )"],   # cut right before each "5. Title" line
    is_separator_regex=True,        # the separator above is a regex
    chunk_size=400,                 # longest entry is 366 characters
    chunk_overlap=0,                # entries stand alone, so no overlap
)

chunks=splitter.split_documents(data)

emb_model=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore=Chroma.from_documents(
    documents=chunks,
    embedding=emb_model,
    persist_directory="chroma_db",
)

retriever=vectorstore.as_retriever(search_kwargs={"k":2})

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a Python debugging expert.\n"
     "Use the reference notes below if they match the problem. Ignore them if they do not.\n"
     "Reply in EXACTLY this format and nothing else:\n"
     "SUMMARY: <2 to 3 sentences: what the code does and what is wrong>\n"
     "CORRECTED CODE:\n"
     "<the full corrected code only>\n\n"
     "Example\n"
     "Code: print('hi'\n"
     "SUMMARY: The code prints hi, but the closing parenthesis is missing.\n"
     "CORRECTED CODE:\n"
     "print('hi')\n\n"
     "Reference notes:\n{notes}"),
    ("human", "Code:\n{code}"),
])

# 1. Local model (runs on your CPU, no token needed)
llm = HuggingFacePipeline.from_model_id(
    model_id="Qwen/Qwen2.5-Coder-1.5B-Instruct",
    task="text-generation",
    pipeline_kwargs={
        "max_new_tokens": 400,       # room for a summary plus the full fixed code
        "temperature": 0.1,          # low = precise, less random
        "do_sample": True,           # needed for temperature to apply
        "return_full_text": False,   # return only the answer, not the prompt
    },
)
chat = ChatHuggingFace(llm=llm)      # adds the model's chat format around the prompt

# 2. Chain: prompt -> model (no parser, because we want plain text)
chain = prompt | chat

# 3. One function that does the whole job
def analyze_code(code: str) -> dict:
    found = retriever.invoke(code)                           # search the PDF entries
    notes = "\n\n".join(d.page_content for d in found)       # join them into one string
    text = chain.invoke({"notes": notes, "code": code}).content   # the model's reply

    # Split the reply at the label "CORRECTED CODE:"
    if "CORRECTED CODE:" in text:
        summary_part, code_part = text.split("CORRECTED CODE:", 1)   # 1 = split only once
    else:
        summary_part, code_part = text, ""                   # model ignored the format

    summary = summary_part.replace("SUMMARY:", "").strip()   # remove the label and spaces
    fixed = code_part.replace("```python", "").replace("```", "").strip()  # remove markdown fences

    return {"summary": summary, "fixed_code": fixed, "notes_used": notes, "raw": text}

# 4. Test (runs only with: python code_debugger.py)
if __name__ == "__main__":
    result = analyze_code("x = 10 / 0")
    print("SUMMARY:", result["summary"])
    print("FIXED CODE:\n", result["fixed_code"])
    print("RAW:\n", result["raw"])