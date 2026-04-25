# PlacementPro - Smart Job Portal 🎯

PlacementPro is a full-stack, AI-powered Placement Management System designed to seamlessly connect students, companies, and administrators. It features a modern, responsive Glassmorphism UI, interactive analytics dashboards, and an automated resume keyword-matching analyzer.

## 🌟 Key Features

* **Role-Based Access Control (RBAC):** Three distinct portals tailored for Students, Companies, and Administrators.
* **AI Resume Analyzer:** Automatically cross-references uploaded PDF/Word resumes against job requirements using keyword extraction and generates a matching score.
* **Job & Application Management:** Companies can post jobs, manage applicants, update statuses, and schedule interviews. Students can browse jobs, apply, and track application lifecycles.
* **Interactive Analytics:** Real-time dashboards powered by Chart.js displaying application statistics, user registrations, and job trends.
* **Approval Workflows:** Admins oversee the platform by approving/rejecting company registrations and job postings to maintain quality control.
* **Automated Notifications:** Users receive instant alerts for interview schedules and application status changes.

## 🛠️ Technology Stack

* **Backend:** Python, Flask, Werkzeug
* **Database:** SQLite (Built-in, zero configuration)
* **Frontend:** HTML5, Custom Glassmorphism CSS (Bootstrap 5 component structure), Bootstrap Icons
* **Data Visualization:** Chart.js
* **Document Processing:** `pdfminer.six` (PDFs), `python-docx` (Word Documents)

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3.8+ installed on your system.

### 1. Clone or Download the Repository
Navigate to the project directory:
```bash
cd "job portal"
```

### 2. Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: If `pdfminer.six` or `python-docx` are commented out in your requirements file, install them manually using `pip install pdfminer.six python-docx` to enable the AI resume analyzer).*

### 4. Run the Application
Start the Flask development server:
```bash
python run.py
```

### 5. Access the Platform
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

## 🔐 Default Admin Credentials

Upon initial setup, the database automatically seeds a default administrator account. You can use these credentials to access the Admin Panel and begin approving companies:

* **Email:** `admin@jobportal.com`
* **Password:** `admin123`
* **Role:** `Admin`

## 🧪 Testing

The platform includes an automated end-to-end testing script (`test_e2e.py`) to verify core functionality including registration, authentication, job posting, application workflows, and admin approvals.

To run the test suite:
```bash
python test_e2e.py
```

## 📝 License
This project is for educational and portfolio purposes. Feel free to modify and adapt it to your specific needs.
