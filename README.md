# 🧠 AI Study Buddy

An AI-powered study assistant that integrates with Canvas LMS to help students learn more effectively. Upload study materials or sync Canvas courses to get AI-generated study paths and personalized tutoring.

---

## 🚀 Overview

**StudyBuddy** connects to **Canvas LMS**, extracts course materials, and uses **Claude AI** + **Supermemory RAG** to:

* Generate AI-based study paths
* Provide context-aware chat tutoring
* Track learning progress

---

## 🏗️ Tech Stack

**Frontend:** React + Vite + Remix Router + Tailwind CSS
**Backend:** FastAPI + SQLite + SQLAlchemy
**AI/RAG:** Anthropic Claude + Supermemory API
**LMS Integration:** Canvas REST API

---

## ⚙️ Setup

### 1. Clone Repository

```bash
git clone https://github.com/vrupak/CBC-Hackathon.git
cd CBC-Hackathon
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

**Backend:** [http://localhost:8000](http://localhost:8000)
**Frontend:** [http://localhost:5173](http://localhost:5173)

---

## 🔑 Requirements

* Node.js 18+
* Python 3.11+
* API keys for Anthropic, Supermemory, and Canvas

---

## 🎯 Next Steps

* Add adaptive study planner & quiz generation
* Visualize progress with charts
* Enable collaborative study mode
* Deploy to cloud (e.g., Render or Vercel)

---

## 🖍️ License

Open-source, created for educational purposes during a hackathon.
