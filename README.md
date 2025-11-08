# 🧠 AI Study Buddy – Product Requirements Document (PRD)

## 1. Overview
An AI-powered study assistant that extracts structured topics from uploaded materials, helps users understand difficult concepts, answers questions contextually, and guides them through a personalized study path.

---

## 2. Goals
- Provide a clear study path based on uploaded material.  
- Answer user questions using extracted content and external knowledge.  
- Adapt explanations based on user understanding level.  
- Help users identify weak areas and improve through interaction.

---

## 3. Core Features (MVP)
### 1. Upload Study Material
- Accept PDFs, text files, or notes.  
- Extract topics and subtopics in logical or importance-based order.  

### 2. Topic Path Generator
- Generate and display a recommended order for studying topics.  

### 3. Interactive Tutoring Chat
- User selects or types a topic they’re struggling with.  
- AI asks diagnostic questions to assess understanding.  
- AI explains concepts at appropriate depth (easy/deep).  
- Provide external references (e.g., YouTube links).  

### 4. Question & Answer Mode
- User asks a question.  
- AI provides an answer with step-by-step explanation.  
- Mentions related topics in that explanation.  

---

## 4. Future Features (Post-MVP)
- Adaptive study planner.  
- Auto-generated quizzes and flashcards.  
- Learning progress visualization.  
- Streaks, badges, and motivation layer.  
- Collaborative study sessions.  

---

## 5. Tech Stack
### Frontend
- **React + Vite** – fast setup, modular components.  
- **Tailwind CSS** – for rapid UI styling.  
- **Axios** – for API communication.  
- **React Router** – for navigation.  

### Backend
- **FastAPI (Python)** – lightweight, async, easy to deploy.  
- **SQLite** – local persistence for hackathon demo.  
- **Supermemory API** – for study material extraction.  
- **OpenAI API** – for reasoning and explanation generation.  

---

## 6. Data Flow
1. User uploads material → FastAPI processes and stores → Supermemory extracts topics.  
2. Frontend displays topics → user selects topic or asks a question.  
3. FastAPI sends request to LLM with context (topics + question).  
4. LLM responds → FastAPI structures and returns response → React UI displays it.  

---

## 7. UI Mock (MVP)
### Pages
- **Home Page:** Upload material + “Generate Study Path” button.  
- **Study Path Page:** List of topics with progress markers.  
- **Chat Page:** Simple chat interface for topic help and Q&A.  

---

## 8. Success Metrics
- Accuracy of topic extraction and ordering.  
- User satisfaction (improved understanding).  
- Relevance and clarity of responses.  

---

## 9. Before Starting
- Plan data structures for topics, subtopics, and chat sessions.  
- Keep APIs modular (upload, extract, chat).  
- Implement early error handling (file too large, extraction failure, etc.).  
- Use mock data for frontend testing before backend integration.  
- Use GitHub Issues or a Kanban board to track feature progress.  

---

## 10. Contributors
- **Project Lead:**  
- **Frontend Developer:**  
- **Backend Developer:**  
- **AI/LLM Integration:**  

---

## 11. License
This project is open-source and developed for educational and demonstration purposes during a 24-hour hackathon.
