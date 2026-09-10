# Mehta AI

**Mehta AI** is a full‑stack, multimodal AI chat assistant — a Flask/Python backend on Vercel serverless functions, a vanilla HTML/CSS/JS frontend, Supabase for auth and persistence, and Groq for LLM inference (text, vision, and audio transcription).

🔗 **Live app:** [mehta-ai-assistance.vercel.app](https://mehta-ai-assistance.vercel.app)

---

## Features

- **Multimodal chat** — text, image (vision), and audio (speech‑to‑text via Whisper) all in one conversation flow
- **Live web grounding** — detects "current info" queries (news, weather, who's the CM/PM, etc., in English and Hindi) and injects fresh DuckDuckGo search results into the prompt instead of letting the model guess from stale training data
- **Automatic model fallback** — every request tries a primary Groq model first and silently falls back to a secondary model if the primary fails
- **Google OAuth + email auth** via Supabase, with per‑user chat history and history persistence
- **Per‑user daily rate limiting** (50 messages/day, admin email exempt) enforced server‑side and tracked in Supabase
- **Voice input** using the Web Speech API, plus dedicated image/audio attachment buttons
- **Light / dark / system theme**, saved locally per device
- **Sign‑in page** with tabbed Sign In / Create Account flows and Google one‑click auth

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask‑CORS |
| Hosting | Vercel serverless functions (`api/index.py`) |
| Auth & DB | Supabase (Auth + Postgres tables: `chat_history`, `chat_limits`) |
| LLM inference | Groq API (chat, vision, and Whisper audio models) |
| Frontend | HTML5, CSS3, vanilla JavaScript, Supabase JS client |
| Web search | DuckDuckGo HTML scrape (no external search API key needed) |

## Project Structure

```
.
├── api/
│   └── index.py        # Flask app — /api/chat and /api/history endpoints
├── assets/              # Static media (login screen video, etc.)
├── index.html           # Main chat UI
├── signin.html           # Sign in / sign up page
├── requirements.txt      # Python dependencies
└── vercel.json           # Routes /api/* to the Flask serverless function
```

## API

### `POST /api/chat`
Accepts `message` (text), `image` (base64 data URL), and/or `audio` (base64 data URL). Requires a Supabase bearer token. Returns `{ reply, history_saved }`.

### `GET /api/history`
Returns the signed‑in user's last 100 chat turns.

### `DELETE /api/history`
Clears the signed‑in user's chat history.

Both endpoints authenticate via an `Authorization: Bearer <supabase_access_token>` header.

## Getting Started

### Prerequisites
- Python 3.9+
- A [Supabase](https://supabase.com) project (Auth + two tables: `chat_history`, `chat_limits`)
- A [Groq](https://console.groq.com) API key

### Setup

```bash
git clone https://github.com/Ra-kumar4216/Mehta-Ai-Assistance-.git
cd Mehta-Ai-Assistance-
pip install -r requirements.txt
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key used for chat/vision/audio inference |
| `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side only) |
| `ALLOWED_ORIGINS` | No | Comma‑separated CORS allow‑list (defaults to the deployed domain + localhost) |
| `GROQ_TEXT_MODEL` / `GROQ_TEXT_MODEL_FALLBACK` | No | Override the default text models |
| `GROQ_VISION_MODEL` / `GROQ_VISION_MODEL_FALLBACK` | No | Override the default vision models |
| `GROQ_AUDIO_MODEL` | No | Override the default Whisper model |
| `ADMIN_EMAIL` | No | Email exempt from the daily message limit |

### Run locally

```bash
python api/index.py
```
Then serve `index.html` / `signin.html` with any static server and point the frontend's Supabase config at your project.

### Deploy
The repo is pre-configured for **Vercel** — `vercel.json` routes all `/api/*` traffic to the Flask function. Push to your Vercel-linked GitHub repo, set the environment variables above in the Vercel dashboard, and deploy.

## Security Notes
- The Supabase key embedded in `index.html` is the **publishable/anon** key, safe for client-side use — the actual authorization boundary is enforced server-side via `verified_user_id()`, which validates the bearer token on every request.
- Responses to "current info" queries are grounded only in live search results, with the retrieval time and source URLs surfaced to the user; the model is explicitly instructed to treat that injected context as untrusted, non-instruction-following data.

## License
No license file is currently included in this repository — all rights reserved by default unless the author adds one.

## Author
**Ratan Kumar Metha**
[GitHub](https://github.com/Ra-kumar4216) · [LinkedIn](https://linkedin.com/in/ratan-kumar-metha) · [Portfolio](https://ratankumar-portfolio.vercel.app)
