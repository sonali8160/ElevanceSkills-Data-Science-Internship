
"""
LangChain FAQ Chatbot using Google Gemini and FAISS.

Project structure:
    ElevanceSkills-Data-Science-Internship/
    ├── .env
    ├── dataset/
    │   └── dataset.csv
    ├── faiss_index/
    └── src/
        ├── langchain_helper.py
        └── internship_dashboard.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import (
    create_stuff_documents_chain,
)


# ==================================================
# 1. PROJECT PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"
CSV_FILE = PROJECT_ROOT / "dataset" / "dataset.csv"
VECTOR_DB_PATH = PROJECT_ROOT / "faiss_index"


# ==================================================
# 2. LOAD GOOGLE API KEY
# ==================================================

load_dotenv(dotenv_path=ENV_FILE, override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError(
        f"GOOGLE_API_KEY is missing. Check your .env file: {ENV_FILE}"
    )


# ==================================================
# 3. INITIALIZE GEMINI
# ==================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1,
)


# ==================================================
# 4. INITIALIZE EMBEDDING MODEL
# ==================================================

# The model downloads from Hugging Face on first use.
# An internet connection is required unless cached locally.
instructor_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)


# ==================================================
# 5. CREATE FAISS VECTOR DATABASE
# ==================================================

def create_vector_db():
    """Read the FAQ CSV and create a local FAISS index."""

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_FILE}"
        )

    print(f"Reading dataset: {CSV_FILE}")

    # cp1252 supports Windows smart quotes such as byte 0x92.
    # utf-8-sig is tried first for standard UTF-8 CSV files.
    try:
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_FILE, encoding="cp1252")

    # Normalize column names to avoid accidental surrounding spaces.
    df.columns = [str(column).strip() for column in df.columns]

    if df.empty:
        raise ValueError("The dataset.csv file contains no data rows.")

    if "prompt" not in df.columns:
        raise ValueError(
            "The CSV must contain a column named 'prompt'. "
            f"Available columns: {df.columns.tolist()}"
        )

    # Remove rows without a question/prompt.
    df = df.dropna(subset=["prompt"])
    df["prompt"] = df["prompt"].astype(str).str.strip()
    df = df[df["prompt"] != ""]

    if df.empty:
        raise ValueError(
            "No usable prompts were found in dataset.csv."
        )

    # Save a temporary normalized CSV in UTF-8.
    # This avoids encoding errors inside CSVLoader.
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".csv",
        delete=False,
    ) as temp_file:
        temp_csv_path = Path(temp_file.name)
        df.to_csv(temp_file, index=False)

    try:
        loader = CSVLoader(
            file_path=str(temp_csv_path),
            source_column="prompt",
            encoding="utf-8",
        )

        documents = loader.load()

    finally:
        # Remove the temporary file even if loading fails.
        temp_csv_path.unlink(missing_ok=True)

    if not documents:
        raise ValueError("CSVLoader did not produce any documents.")

    print(f"Loaded {len(documents)} FAQ documents.")
    print("Creating embeddings and FAISS index...")

    vector_db = FAISS.from_documents(
        documents=documents,
        embedding=instructor_embeddings,
    )

    vector_db.save_local(str(VECTOR_DB_PATH))

    print(f"FAISS index saved at: {VECTOR_DB_PATH}")
    print("Knowledge base created successfully!")

    return vector_db


# ==================================================
# 6. LOAD FAISS AND CREATE QA CHAIN
# ==================================================

def get_qa_chain():
    """Load the FAISS index and build the retrieval QA chain."""

    index_file = VECTOR_DB_PATH / "index.faiss"
    metadata_file = VECTOR_DB_PATH / "index.pkl"

    if not index_file.exists() or not metadata_file.exists():
        raise FileNotFoundError(
            "FAISS index is missing or incomplete. "
            "Run create_vector_db() first."
        )

    vector_db = FAISS.load_local(
        str(VECTOR_DB_PATH),
        instructor_embeddings,
        # Only load a FAISS index that you created and trust.
        allow_dangerous_deserialization=True,
    )

    retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4},
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Answer the user's question using the provided context.

Use the source information accurately.
Do not invent facts or make unsupported assumptions.
If the answer is not present in the context, say:
"I don't know."

Context:
{context}""",
            ),
            ("human", "{input}"),
        ]
    )

    document_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt,
    )

    retrieval_chain = create_retrieval_chain(
        retriever=retriever,
        combine_docs_chain=document_chain,
    )

    return retrieval_chain


# ==================================================
# 7. RUN CHATBOT DIRECTLY
# ==================================================

if __name__ == "__main__":
    try:
        index_file = VECTOR_DB_PATH / "index.faiss"
        metadata_file = VECTOR_DB_PATH / "index.pkl"

        if not index_file.exists() or not metadata_file.exists():
            create_vector_db()

        qa_chain = get_qa_chain()

        print("\nFAQ Chatbot is ready!")
        print("Type 'exit' to stop.\n")

        while True:
            question = input("Enter your question: ").strip()

            if question.lower() in {"exit", "quit"}:
                print("Chatbot stopped.")
                break

            if not question:
                print("Please enter a question.")
                continue

            result = qa_chain.invoke({"input": question})

            print("\nAnswer:")
            print(result["answer"])

            print("\nSource documents:")

            for index, document in enumerate(
                result.get("context", []),
                start=1,
            ):
                print(f"\nSource {index}:")
                print(document.page_content)

            print("\n" + "-" * 50)

    except Exception as error:
        print(f"\nChatbot error: {type(error).__name__}: {error}")
