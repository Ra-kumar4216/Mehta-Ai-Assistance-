# 🎙️ Mehta AI — Your Intelligent Web Assistant

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/AI-Groq%20Llama%203-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Database-Supabase-emerald?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Hosting-Vercel-black?style=for-the-badge" />
</p>

> **Talk, type, or show. Mehta is built to understand everything.**

Meet **Mehta AI**, a lightning-fast, highly secure, and fully web-based intelligent assistant. Powered by the latest Groq models (Llama 3) and hosted seamlessly on Vercel, Mehta goes beyond simple text chats. It features real-time internet search, voice input, image analysis, and a natural conversational flow—all wrapped in a clean, user-friendly interface.

---

## 🌐 Live Demo
**Try it out here:** [Mehta AI Live Application](https://mehta-ai-assistance.vercel.app/)

---

## ✨ What Makes Mehta Stand Out?

- ⚡ **Blazing Fast Responses:** Powered by Groq's Llama-3.3-70b (Text) and Llama-3.2-90b (Vision) for near-instant inference.
- 👁️ **Vision & Image Analysis:** Upload any image, and Mehta will accurately analyze and describe its contents.
- 🎙️ **Hands-Free Voice Input:** Integrated Web Speech API allows you to talk to the AI naturally instead of typing.
- 🔐 **Secure Authentication:** Seamless Google Login integration powered by Supabase OAuth.
- 💾 **Persistent Memory:** All your conversations are securely saved in a PostgreSQL database and retrieved instantly upon login.
- 🛡️ **Smart Rate Limiting:** A fair usage policy (50 chats/24 hours for standard users) tracked entirely server-side to prevent API abuse, with unlimited access reserved for admins.
- 🌍 **Multilingual Support:** Fluent in English, Hindi, Hinglish, Tamil, and Telugu, adapting instantly to your preferred language.
- 🔍 **Real-Time Web Search:** Scrapes the internet in real-time to provide up-to-date facts and context when answering questions.

---

## 🏗️ Under the Hood (Tech Stack)

I built this project to be lightweight on the frontend and highly scalable on the backend:
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (No heavy frameworks, ensuring ultra-fast load times). Markdown rendering is handled by Marked.js.
- **Backend:** Python (Flask) deployed as Vercel Serverless Functions.
- **Database:** Supabase (PostgreSQL) for user management and chat history.
- **AI Provider:** Groq Cloud API for ultra-low latency LLM processing.

---

## ⚙️ Local Development Setup
If you'd like to run this project locally or fork it for your own use, you will need to set up the following Environment Variables. 

Create a `.env` file in the root directory and add:

```env
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_role_key
ADMIN_EMAIL=your_admin_email@gmail.com
GROQ_TEXT_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
