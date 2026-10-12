# ElevanceSkills Data Science Internship  
## Customer Service Chatbot with AI-Powered Support Workflows

A Python-based customer service chatbot project that combines FAQ question answering with six additional task modules for sentiment analysis, support ticket management, knowledge-base monitoring, retrieval-augmented generation (RAG), evidence processing, and multilingual conversations.

The project extends the original customer service chatbot and its existing FAQ dataset with modular features designed to demonstrate practical AI, data processing, and customer support automation concepts.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Configuration](#configuration)
- [Run the Application](#run-the-application)
- [Run Tests](#run-tests)
- [Dataset](#dataset)
- [Security](#security)
- [Future Improvements](#future-improvements)

## Project Overview

Customer support teams handle a wide range of customer queries, unresolved issues, documents, and multilingual conversations. This project demonstrates how Python-based automation and AI-related techniques can help organize these workflows.

The application provides a Streamlit interface where users can explore the original chatbot and six task modules through a unified dashboard.

## Features

### Original Customer Service Chatbot
- Answers frequently asked questions using the existing CSV dataset.
- Includes knowledge-base functionality using LangChain.
- Supports an optional Google Gemini-powered question-answering workflow.

### Task 1: Sentiment Analysis and Escalation
- Analyzes customer messages for sentiment, tone, urgency, and frustration.
- Considers conversation history.
- Identifies potential risk indicators.
- Provides escalation-related signals and analysis results.

### Task 2: Support Ticket Management
- Extracts useful customer and issue information from conversations.
- Identifies missing information.
- Determines ticket priority and service-level agreement (SLA) details.
- Routes tickets to suitable support agents.
- Supports duplicate detection, grouping, and handoff summaries.

### Task 3: Knowledge-Base Update Pipeline
- Scans documents for new or changed content.
- Checks document quality and duplicates.
- Supports document versioning and scheduled activation.
- Demonstrates access control, monitoring, retry, and rollback workflows.

### Task 4: Retrieval-Augmented Generation (RAG) Assistant
- Retrieves relevant knowledge documents.
- Uses document metadata, versions, dates, and access levels.
- Supports evidence-based responses and citations.
- Demonstrates handling of insufficient or restricted information.

### Task 5: Evidence and OCR Processing
- Processes supported image, PDF, text, and CSV evidence.
- Extracts information for comparison with customer claims.
- Supports clarification for uncertain or mismatched information.
- Demonstrates data masking and retention-related handling.

Note: OCR for image files requires Tesseract OCR to be installed separately.

### Task 6: Multilingual Chat
- Demonstrates baseline language detection for English, Hindi, Marathi, and Spanish.
- Handles mixed-language messages.
- Demonstrates conversation context, session isolation, and restoration.
- A rule-based demonstration rather than a production translation service.

## Technology Stack

- **Programming Language:** Python
- **Web Interface:** Streamlit
- **AI and Language Processing:** LangChain, Google Gemini integration
- **Data Processing:** Pandas
- **Retrieval and Vector Search:** FAISS, Sentence Transformers
- **Document Processing:** PyPDF, PyMuPDF, Pillow
- **OCR:** Pytesseract and Tesseract OCR
- **Testing:** Pytest and Python unittest

## Project Structure

```text
ElevanceSkills-Data-Science-Internship/
├── dataset/
│   └── dataset.csv
├── src/
│   ├── internship_dashboard.py
│   ├── langchain_helper.py
│   └── main.py
├── task1/
│   ├── analyzer.py
│   ├── conversation.py
│   ├── escalation.py
│   ├── models.py
│   └── tone.py
├── task2/
│   ├── duplicate.py
│   ├── extractor.py
│   ├── grouping.py
│   ├── routing.py
│   ├── sla.py
│   └── ticket_workflow.py
├── task3/
│   ├── monitoring.py
│   ├── pipeline.py
│   ├── quality.py
│   └── security.py
├── task4/
│   └── rag_assistant.py
├── task5/
│   └── evidence_processor.py
├── task6/
│   └── multilingual_chat.py
├── tests/
│   ├── run_all_tests.py
│   └── task1_test_cases.py
│   └── task2_test_cases.py
│   └── task3_test_cases.py
│   └── task4_test_cases.py
│   └── task5_test_cases.py
│   └── task6_test_cases.py
├── requirements.txt
└── README.md
```

## Installation and Setup

### Prerequisites

- Python 3.11 recommended
- Git
- Visual Studio Code or another Python editor
- Internet access for installing dependencies and using optional online AI services

### 1. Clone the repository

```bash
git clone https://github.com/sonali8160/ElevanceSkills-Data-Science-Internship.git
cd ElevanceSkills-Data-Science-Internship
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

The original chatbot's optional Gemini-powered functionality requires a valid Google API key.

1. Create a local file named `.env` in the project root.
2. Add your key:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

3. Save the file.

Replace the placeholder with your own valid key. Never commit your actual API key or `.env` file to GitHub.

Some dashboard functionality can be demonstrated without configuring the optional API integration.

## Run the Application

### Combined dashboard

From the project root, run:

```bash
python -m streamlit run src/internship_dashboard.py
```

Streamlit will display a local URL in the terminal, usually:

```text
http://localhost:8501
```

Open that URL in your browser.

The dashboard contains tabs for the original chatbot and Tasks 1–6.

### Original chatbot only

To run the original chatbot interface separately:

```bash
python -m streamlit run src/main.py
```

The original knowledge-base workflow may require the configured Google API key and successful creation of its vector database.

## Run Tests

To run all six included task test suites from the project root:

```bash
python tests/run_all_tests.py
```

To run an individual test suite:

```bash
python tests/task1_test_cases.py
python tests/task2_test_cases.py
python -m unittest discover -s tests -p "task3_test_cases.py" -v
python -m unittest discover -s tests -p "task4_test_cases.py" -v
python -m unittest discover -s tests -p "task5_test_cases.py" -v
python -m unittest discover -s tests -p "task6_test_cases.py" -v
```

Review the test output to identify any failed cases or environment-related issues.

## Dataset

The project retains its original FAQ dataset at:

`dataset/dataset.csv`

The dataset supports the original customer service question-answering functionality. The code may require Windows-1252 encoding when reading this CSV.

## Security

- Keep API keys and credentials out of source code and Git history.
- Keep `.env`, virtual environments, and Python cache files out of GitHub.
- Do not upload private customer information or confidential datasets.
- Rotate any credential that has been accidentally exposed.
- Apply appropriate access controls and data protection measures before adapting the demonstration for real customer data.

## Future Improvements

- Improve intent detection and sentiment classification with evaluated machine learning models.
- Add a persistent database for customer support tickets.
- Integrate the chatbot with a real support platform.
- Add automated deployment and continuous integration.
- Evaluate retrieval quality and response accuracy using a larger, representative test dataset.
- Expand multilingual support with dedicated language models.

## Learning Outcomes

This project provides practical experience with:

- Python application development
- Streamlit dashboard development
- Data handling and text processing
- AI-powered question answering
- Retrieval-augmented generation concepts
- Support workflow automation
- Document and evidence processing
- Modular code organization and testing

## Disclaimer

This repository is an educational and demonstration project. Its outputs, security checks, OCR results, routing decisions, and AI-generated responses should be evaluated before any real-world use. The included test suites do not establish production readiness.

---

**Author:** Sonali Jadhav

**Project:** ElevanceSkills Data Science Internship — Customer Service Chatbot
