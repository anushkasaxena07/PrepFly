# 🚀 PrepFly - Comprehensive Project Overview

**PrepFly** is an AI-powered placement preparation platform specifically designed for Computer Science students. It unifies coding assessments, resume analysis, AI mock interviews, and analytics into a single cohesive platform.

Here is everything you need to know about the project.

---

## 🏗️ 1. Architecture & Tech Stack

PrepFly uses a modern decoupled architecture:

### Frontend
- **Framework**: React with Vite for lightning-fast builds and HMR.
- **Styling**: Tailwind CSS for rapid UI development.
- **Routing**: React Router for navigation between the dashboards (Student, Admin, Super Admin).
- **Hosting**: Deployed on **Vercel**.

### Backend
- **Framework**: Python Flask.
- **Role**: Serves as the API Gateway orchestrating business logic, AI calls, and database operations.
- **Hosting**: Deployed on **Railway**.

### Infrastructure & Databases
- **Supabase PostgreSQL**: Relational database storing user data, questions, performance metrics, and organization info.
- **Supabase Auth**: Manages user authentication (signups, logins) and issues JWTs.
- **Supabase Storage**: Object storage for user resumes (PDFs) and other assets.

### External AI & Services
- **Google Gemini**: The core AI engine. Powers "Ava" (the AI interviewer), evaluates resumes for ATS compatibility, and generates dynamic questions.
- **Judge0 API**: An isolated, secure code execution sandbox used for evaluating student coding submissions.
- **Razorpay**: Handles payment processing for subscriptions.

---

## ✨ 2. Core Modules & Features

The platform is divided into three main portals based on user roles:

### 👨‍🎓 Student Portal
- **AI Voice Interviews**: Practice realistic voice interviews with *Ava* based on your resume, role, and difficulty level.
- **Peer-to-Peer Mock Interviews**: Practice live with fellow students.
- **Coding Assessment Environment**: Practice coding with multiple languages and hidden test cases.
- **Resume Intelligence**: Get AI-driven resume scores, ATS compatibility checks, and keyword analysis.
- **Analytics Dashboard**: Track interview progress, coding performance, and placement readiness.

### 🏫 Admin Portal
- **Question Bank & AI Generation**: Manage questions manually or generate them using AI.
- **Student Management & Analytics**: Track student performance and placement readiness across the organization.
- **Assessments & Interviews**: Configure specific interview scenarios and coding tests.
- **Reports**: Generate downloadable PDF/Excel reports on student progress.

### 👑 Super Admin Portal
- **Organization & Subscription Management**: Manage different organizations using the platform and track Razorpay subscriptions.
- **Global Analytics & Revenue**: View high-level metrics and revenue dashboards.
- **Platform Configuration**: Manage the multi-tenant architecture and platform-wide settings.

---

## 📂 3. Project Structure

The repository is structured as a monorepo with separate folders for frontend and backend components:

```text
PrepFly (Root)
│
├── f_frontend/             # React + Vite Frontend application
│   ├── src/                # UI Components, pages, and API service hooks
│   └── package.json        # Node dependencies
│
├── f_backend/              # Flask Backend application
│   ├── services/           # Business logic and external API integrations
│   ├── uploads/            # Temporary file storage (e.g., for processing resumes)
│   ├── app.py              # Main Flask application entry point
│   ├── payment.py          # Razorpay integration logic
│   ├── subscription.py     # Subscription tier management
│   ├── webhook.py          # Webhook handlers for external services
│   └── requirements.txt    # Python dependencies
│
└── scraper/                # Potentially for gathering external placement data or questions
```

---

## 🚀 4. How to Run Locally

If you need to spin up the project on your local machine for development, follow these steps:

### Prerequisites
You need Node.js (for the frontend) and Python 3.11+ (for the backend).

### Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd f_backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in `f_backend/` with the following variables:
   ```env
   GEMINI_API_KEY=your_key
   SUPABASE_URL=your_url
   SUPABASE_SERVICE_KEY=your_key
   SMTP_EMAIL=your_email
   SMTP_PASSWORD=your_password
   GOOGLE_CLIENT_ID=your_client_id
   RAZORPAY_KEY_ID=your_razorpay_key
   RAZORPAY_KEY_SECRET=your_razorpay_secret
   JWT_SECRET_KEY=your_jwt_secret
   FRONTEND_URL=http://localhost:5173
   ```
4. Run the Flask server:
   ```bash
   python app.py
   ```

### Frontend Setup
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd f_frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

## 🎯 5. Current Roadmap & Next Steps
Based on the project's documentation, some features are still in active development:
- **Peer-to-Peer Live Interview Capabilities**
- **Live Coding Collaboration**
- **Company-Specific Interview Simulation**
- **Mobile Application Development**
