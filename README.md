# ResumeAI: AI-Powered Career Intelligence Platform

[![Live Demo](https://img.shields.io/badge/Live_Demo-resume--ai--8xd3.onrender.com-blue?style=for-the-badge)](https://resume-ai-8xd3.onrender.com)

> An intelligent, job-seeker-focused platform that leverages the Google Gemini LLM to analyze resumes, predict ATS scores, and match candidates to real-time remote opportunities.

---

## 🎯 Project Overview

Navigating the modern job market is incredibly difficult due to Applicant Tracking Systems (ATS) that filter out candidates before a human ever reads their resume. **ResumeAI** solves this by empowering job seekers with the same technology used by enterprise recruiters.

Instead of guessing why you were rejected, ResumeAI provides:
- **Instant ATS Scoring:** Understand exactly how an algorithm views your resume.
- **AI Bullet-Point Optimization:** Automatically rewrite weak achievements into metrics-driven, high-impact statements.
- **Smart Job Matching:** Browse active, remote jobs tailored to your extracted skills.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Deep Resume Parsing** | Extracts core skills, experiences, and education using NLP. |
| **Gemini AI Integration** | Uses Google's Gemini LLM to generate actionable feedback and optimize bullet points. |
| **ATS Score Prediction** | Calculates compatibility scores and identifies missing critical keywords. |
| **Dynamic Job Matching** | Real-time connections to remote job listings based on profile alignment. |
| **Secure Authentication** | OAuth 2.0 Google Login and secure session management. |
| **Asynchronous Notifications** | Zero-blocking email dispatch system using daemon threading. |

---

## 🛠️ Technology Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | Python 3, Flask, SQLAlchemy |
| **Frontend** | HTML5, CSS3, JavaScript (Responsive UI) |
| **Artificial Intelligence** | Google Gemini API (LLM) |
| **Database** | SQLite (Production ready via SQLAlchemy) |
| **Authentication** | Google OAuth, custom JWT, Twilio (mock) |
| **Deployment** | Render, Git |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/akumalla2711-a11y/RESUME-AI.git
cd RESUME-AI
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory and add:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_super_secret_key
GEMINI_API_KEY=your_google_gemini_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
# Email Configuration (Optional)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### 5. Run the Application
```bash
flask run
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🧠 How It Works

1. **Upload & Parse:** Users upload their resume. The backend extracts the raw text and standardizes it.
2. **AI Analysis:** The text is securely transmitted to the Gemini API, where the LLM evaluates structure, grammar, and impact.
3. **Score Generation:** An ATS compatibility score is generated alongside a predicted career category.
4. **Actionable Feedback:** The Optimization Lab presents before-and-after suggestions to rewrite weak bullet points.
5. **Job Board Integration:** The extracted skills are used to query remote job APIs, returning tailored opportunities.

---

## 🔒 Security & Performance

- **Zero-Blocking Architecture:** Heavy external API requests (Gemini, SMTP) are handled via asynchronous background threads to ensure the UI remains instantly responsive.
- **Data Privacy:** Resume data is processed in-memory and never stored permanently without user consent.
- **Robust Auth:** Standardized password hashing (Werkzeug) and Google OAuth integration.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request with your improvements.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
