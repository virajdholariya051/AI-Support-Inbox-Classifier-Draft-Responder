# AI Support Inbox Classifier & Draft Responder
**M.Sc. IT Academic Project**

An intelligent customer support management system designed to process, classify, prioritize, and generate response drafts for incoming customer emails using local machine learning, heuristic rules, and human-in-the-loop approval workflows.

---

## 🌟 Key Features

1. **Local Machine Learning Classification (`backend/email_classifier.py`):**
   - Categorizes incoming support requests into 5 core support domains:
     - `Technical Support`
     - `Billing & Payments`
     - `Account Access`
     - `Feature Request`
     - `General Inquiry`
   - Powered by Scikit-learn (TF-IDF Vectorizer + Multinomial Naive Bayes) with keyword heuristic fallback.
   - Runs 100% locally on Windows without requiring paid external API keys.

2. **Urgency & Severity Detection (`backend/urgency_detector.py`):**
   - Identifies urgency levels: `Low`, `Medium`, `High`, and `Critical`.
   - Scores tickets (0–100) using outage signals, stress keywords, capitalization patterns, and punctuation intensity.

3. **Churn & Legal Risk Detection (`backend/risk_detector.py`):**
   - Detects customer churn threats ("cancel subscription", "switching to competitor").
   - Identifies regulatory, legal, and compliance risks ("lawsuit", "GDPR breach", "report to FTC").
   - Flags public reputation threats ("taking this to social media", "manager escalation").

4. **Automated Team Assignment & SLA Routing (`backend/team_assignment.py`):**
   - Routes tickets to specialized operational teams:
     - `Tier 1 Support`
     - `Tier 2 / Tech Support`
     - `Billing Team`
     - `Accounts & Security`
     - `Product Management`
     - `Executive Escalations`
   - Dynamically calculates target SLA response hours.

5. **Knowledge Base Retrieval & Grounded Drafting (`backend/knowledge_base.py`, `backend/draft_generator.py`):**
   - Matches incoming queries against approved troubleshooting articles using cosine similarity.
   - Strictly enforces that only **approved** articles (`is_approved = 1`) are cited.
   - Synthesizes professional, empathetic response drafts or provides graceful fallbacks for novel questions.

6. **Human-in-the-Loop Review & Simulated Sending (`backend/approval_service.py`):**
   - Complete draft lifecycle state machine: `PENDING_APPROVAL` ➔ `APPROVED` ➔ `SENT` (or `REJECTED`).
   - Editing an approved draft strictly resets its status back to `PENDING_APPROVAL` to ensure quality.
   - Unapproved or rejected drafts are strictly blocked from being sent.
   - Simulated sending outputs structured dispatch receipts without connecting to external mail servers.

7. **Streamlit Multi-Page Web Interface (`app.py`):**
   - **Dashboard:** KPI summary cards, urgency donut chart, category bar charts, workload distribution, and audit log feed.
   - **Inbox:** Filterable ticket table with urgency badges, risk warnings, and conversation inspection.
   - **Analyze Email:** Interactive diagnostic intake lab for real-time ticket testing and preview.
   - **Draft Responses:** Review station for editing, approving, rejecting, and simulating response dispatch.
   - **Knowledge Base:** Directory of solutions with approval toggles and article creation form.
   - **Reports & CSV Import:** Interactive CSV upload for batch ingestion, sample data loader, and CSV report export.

---

## 📁 Project Architecture & File Structure

```text
C:\skips\sem-3\New folder\
├── .agent/
│   ├── MEMORY.md                 # Project architecture, schema, & design decisions
│   ├── CONTEXT.md                # Environment & implementation status
│   └── TASKS.md                  # Detailed task backlog and completion tracking
├── backend/
│   ├── __init__.py
│   ├── database.py               # SQLite schema, parameterized queries, & CRUD operations
│   ├── email_classifier.py       # TF-IDF + Naive Bayes classification & heuristics
│   ├── urgency_detector.py       # Urgency scoring (Critical, High, Medium, Low)
│   ├── team_assignment.py        # Team routing matrix & SLA calculation
│   ├── risk_detector.py          # Customer churn & legal risk detector
│   ├── knowledge_base.py         # Cosine similarity retrieval of approved KB articles
│   ├── draft_generator.py        # Structured draft synthesis & fallback handling
│   ├── approval_service.py       # Review workflow, approval state transitions & simulated send
│   └── email_processor.py        # Coordinated pipeline & batch CSV intake
├── data/
│   ├── initial_kb.json           # Seed knowledge base troubleshooting guides
│   └── sample_emails.csv         # 15 realistic customer support emails
├── tests/
│   ├── __init__.py
│   ├── test_database.py          # Database initialization & CRUD tests
│   ├── test_classifier.py        # Category classification & urgency tests
│   ├── test_urgency_team.py      # Team routing & SLA tests
│   ├── test_risk_detector.py     # Churn & legal risk detector tests
│   ├── test_knowledge_base.py    # Approved KB retrieval tests
│   ├── test_draft_generator.py   # Grounded drafting & fallback tests
│   ├── test_approval_service.py  # Review states & send restrictions tests
│   └── test_csv_validation.py    # CSV validation & batch import tests
├── app.py                        # Streamlit multi-page interface & analytics dashboard
├── requirements.txt              # Project dependencies
├── support_inbox.db              # SQLite database (auto-created on first run)
└── README.md                     # Documentation & setup guide
```

---

## 🛠️ Windows Setup & Installation

### Step 1: Ensure Python is Installed
Verify Python (3.10+) is installed and accessible in your Windows command prompt or PowerShell:
```powershell
python --version
```

### Step 2: Navigate to Project Directory
```powershell
cd "C:\skips\sem-3\New folder"
```

### Step 3: Install Required Dependencies
Run:
```powershell
python -m pip install -r requirements.txt
```

---

## 🚀 Running the Application

Launch the Streamlit web dashboard:
```powershell
streamlit run app.py
```
*(or alternatively using Python module syntax)*:
```powershell
python -m streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the full pytest suite with verbose output:
```powershell
pytest -v
```
*(or via Python module)*:
```powershell
python -m pytest -v
```

All 45 automated unit tests execute with 100% pass rate.

---

## 📖 Main Workflows Walkthrough

1. **Load Sample Dataset:**
   - In the Streamlit sidebar, select **📈 Reports & CSV Import**.
   - Under the **CSV Batch Intake** tab, click **"📥 Load Built-in sample_emails.csv"** (or use the one-click load button on the Dashboard).
   - 15 realistic support tickets will be classified, urgency-scored, risk-checked, and stored with synthesized response drafts.

2. **Inspect Inbox & High-Risk Tickets:**
   - Navigate to **📥 Inbox**.
   - Filter by Urgency (e.g., `Critical`) or Category (`Technical Support`).
   - Open any ticket to inspect the email body, risk alerts, and assigned support team.

3. **Review & Approve Response Drafts:**
   - Navigate to **✍️ Draft Responses**.
   - Review pending drafts generated using approved knowledge base articles.
   - Click **"💾 Save Edits"** after modifying text; observe that status immediately resets to `PENDING_APPROVAL`.
   - Click **"✅ Approve"** with reviewer name.
   - Notice that the **"🚀 Simulate Send"** button becomes active. Click it to simulate dispatch and inspect the delivery receipt.

4. **Live Single Ticket Diagnostic:**
   - Navigate to **🔍 Analyze Email**.
   - Enter any custom message, e.g.:
     - *"I want to cancel my subscription and speak to a manager immediately!"*
   - Click **"Run Diagnostic Analysis"** to see live category probability, churn risk flag, team escalation to Executive Escalations, and draft preview.

---

## 🔒 Security & Privacy Notice
- This application runs entirely locally on your Windows workstation.
- SQLite database is stored locally as `support_inbox.db`.
- No customer data or emails are sent to external cloud APIs or third-party email servers.
