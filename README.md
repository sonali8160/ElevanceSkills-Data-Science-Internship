<<<<<<< HEAD
# ElevanceSkills Data Science Internship — Customer Service Chatbot

This repository extends the original training project: a customer-service FAQ chatbot backed by the original `dataset/dataset.csv`. The internship work adds six task modules to the same project; it does not replace the training dataset with an unrelated dataset or create an unrelated project.

## Project features

- **Original chatbot:** FAQ question answering from the existing CSV dataset; optional Gemini-powered knowledge-base functionality.
- **Task 1 — Sentiment, tone and escalation:** sentiment/frustration/urgency/sarcasm signals, confidence scores, conversation history, high-risk detection, tone guidance and time-aware escalation.
- **Task 2 — Support ticket workflow:** field extraction, missing-information requests, priority, SLA calculations, routing, duplicate/group detection and masked handoff summaries.
- **Task 3 — Knowledge-base update pipeline:** document change detection, duplicate/invalid-document handling, quality checks, versioning, scheduled activation, retry/rollback logic, access control and monitoring.
- **Task 4 — RAG knowledge assistant:** metadata-aware document retrieval, role/access checks, date/version-aware policies, citations, and refusal when evidence is insufficient or unsafe.
- **Task 5 — Evidence/OCR processing:** image/PDF/text/CSV evidence extraction, comparison against customer claims, clarification for uncertain/mismatched evidence, masking and retention handling. OCR images locally with Tesseract installed.
- **Task 6 — Multilingual sessions:** English, Hindi, Marathi and Spanish baseline detection, mixed-language messages, entity preservation, context retention, session isolation and restoration. This is a rule-based demonstrator, not a production translation service.

## Repository structure

```text
ElevanceSkills-Data-Science-Internship/
├── dataset/
│   └── dataset.csv              # Original training FAQ dataset
├── src/
│   ├── internship_dashboard.py  # Combined website for original chatbot + Tasks 1–6
│   ├── langchain_helper.py      # Original chatbot knowledge-base helper
│   └── main.py                 # Original chatbot entry point
├── task1/                       # Sentiment, tone and escalation
├── task2/                       # Support ticket workflow
├── task3/                       # Knowledge-base update pipeline
├── task4/                       # RAG assistant
├── task5/                       # Evidence and OCR processing
├── task6/                       # Multilingual chat and sessions
├── tests/                       # Included test suites and combined test runner
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11 recommended.
- Tesseract OCR is an optional system dependency for OCR on image files.
- A Google API key is only required for the optional Gemini mode / original vector knowledge-base creation. Do not commit API keys or `.env` files.

## Setup on Windows

Open a terminal in the repository root (the folder containing `requirements.txt`) and run:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.

## Run the combined website

From the repository root:

```powershell
python -m streamlit run src/internship_dashboard.py
```

The website contains tabs for the original chatbot and each of Tasks 1–6. The original FAQ mode reads `dataset/dataset.csv`; the combined dashboard includes a local dataset-answer mode so basic FAQ matching can be demonstrated without an API key. The optional Gemini mode requires `GOOGLE_API_KEY` in a local `.env` file or Streamlit deployment secrets.

To run only the original chatbot interface instead:

```powershell
python -m streamlit run src/main.py
```

## Run tests

Run all included task suites from the repository root:

```powershell
python tests/run_all_tests.py
```

Or run individual suites:

```powershell
python tests/task1_test_cases.py
python tests/task2_test_cases.py
python -m unittest discover -s tests -p "task3_test_cases.py" -v
python -m unittest discover -s tests -p "task4_test_cases.py" -v
python -m unittest discover -s tests -p "task5_test_cases.py" -v
python -m unittest discover -s tests -p "task6_test_cases.py" -v
```

The test runner runs only test files included in this repository. Test success demonstrates the included scenarios; it does not by itself prove production readiness or guarantee an internship stipend.

## Dataset and encoding

The original CSV is retained in `dataset/dataset.csv`. Its current text encoding is Windows-1252, so code that reads it should use an encoding fallback (the chatbot helper does this). Do not replace it with an unrelated dataset.

## GitHub submission checklist

1. Commit the complete project, including `dataset/`, `src/`, `task1/` through `task6/`, `tests/`, `requirements.txt`, and this README.
2. Confirm the repository is **Public** and opens in a private/incognito browser window without signing in.
3. Confirm the README commands match files in the repository.
4. Create a clean Python environment, install requirements, run the combined test command, and launch the dashboard.
5. Test the public deployment URL separately if submitting one; a public GitHub repository does not automatically mean the Streamlit app is deployed.
6. Check for secrets, local paths, temporary files, and generated caches before committing.
7. Only submit to ElevanceSkills after you have reviewed the final repository URL and any required report/details. The provider's instructions state that submission is one-time and cannot be edited afterward.

## Original project and internship extension

The original FAQ chatbot and dataset remain part of this repository. The internship modules are added as separate task packages and exposed through the combined Streamlit dashboard to make mentor review easier.
=======
# ElevanceSkills-Data-Science-Internship
>>>>>>> 494679dccec13d096de55b885aa60ead4abccefd
