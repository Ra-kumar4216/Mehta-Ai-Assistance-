# 🎙️ Mehta — Voice-Controlled AI Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/AI-DeepSeek%20via%20OpenRouter-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/TTS-gTTS%20%7C%20pyttsx3-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge" />
</p>

> **Talk to your computer. Mehta listens, thinks, and acts.**

Mehta is an offline-friendly, voice-controlled AI assistant for Windows, macOS, and Linux. Speak a command or ask a question — Mehta hears you, processes your intent, and either performs an OS-level action or gets a natural-language answer from **DeepSeek** via the free [OpenRouter](https://openrouter.ai) API.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎙️ **Voice Input** | Microphone capture via `sounddevice` (no PyAudio needed) with auto ambient-noise calibration |
| 🔊 **Voice Output** | Online gTTS or offline pyttsx3 — your choice |
| 🤖 **AI Replies** | Powered by DeepSeek on OpenRouter (free tier available) |
| 🖥️ **PC Control** | Open websites, Google Search, download files, manage files & folders, shutdown / restart |
| 🔐 **Safety Mode** | Confirmation prompts before destructive actions (deletions, shutdown) |
| 💬 **Conversation Memory** | Maintains rolling context across turns for natural multi-turn dialogue |
| ⏰ **Wake Word Support** | Optionally activate only on a custom wake phrase (e.g. *"Hey Mehta"*) |
| ⚙️ **Fully Configurable** | All settings via `.env` file — no source-code edits needed |
| 🐍 **Python 3.10 – 3.14** | Uses `sounddevice` instead of PyAudio for broad Python version support |

---

## 🗣️ Voice Commands

| Say this… | What happens |
|---|---|
| *"Open youtube"* | Opens youtube.com in your browser |
| *"Search for Python tutorials"* | Google search opens in browser |
| *"Download \<file\> from \<url\>"* | File saved to `~/Downloads/Mehta/` |
| *"List files"* | Reads out files in your Mehta downloads folder |
| *"Create folder projects"* | Creates a sub-folder |
| *"Delete report.pdf"* | Deletes file (with confirmation) |
| *"Shutdown"* | Shuts down the computer (with confirmation) |
| *"Restart"* | Restarts the computer (with confirmation) |
| *"Exit"* / *"Quit"* / *"Bye"* | Closes the assistant |
| Anything else | Sent to DeepSeek AI for a conversational reply |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Ra-kumar4216/Mehta-Ai-Assistance-
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Linux only:** also install `mpg123` for audio playback:
> ```bash
> sudo apt install mpg123
> ```

### 3. Get your free API key

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to **Keys** → **Create Key**
3. Copy the key

### 4. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and set:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 5. Run

```bash
python mehta_assistant.py
```

Speak when you hear the prompt. Say **"exit"** or **"goodbye"** to stop.

---

## ⚙️ Configuration

All settings live in `.env` (no code edits required):

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat` | Any model on OpenRouter |
| `TTS_ENGINE` | `gtts` | `gtts` (online) or `pyttsx3` (offline) |
| `TTS_LANGUAGE` | `en` | Language code for gTTS |
| `TTS_RATE` | `170` | Speech rate in WPM (pyttsx3 only) |
| `SAFETY_MODE` | `true` | Confirm before destructive actions |
| `MAX_HISTORY_TURNS` | `10` | Conversation turns kept in context |
| `LISTEN_TIMEOUT` | `7` | Seconds to wait for speech to start |
| `PHRASE_TIME_LIMIT` | `15` | Max seconds for one utterance |
| `WAKE_WORD` | *(none)* | Activation phrase, e.g. `hey mehta` |

---

## 🏗️ Architecture

```
mehta_assistant.py
│
├── listen()          — Microphone → text  (sounddevice + Google STT)
├── speak()           — Text → voice       (gTTS or pyttsx3)
├── clean_text()      — Strips markdown / emojis for clean TTS
├── parse_command()   — Regex intent detection
├── perform_action()  — OS-level execution (browser, files, power)
└── generate_reply()  — OpenRouter / DeepSeek AI response
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `SpeechRecognition` | Google STT wrapper |
| `sounddevice` | Microphone capture (no PyAudio) |
| `numpy` | Audio buffer processing |
| `requests` | OpenRouter API calls |
| `gTTS` | Online text-to-speech |
| `python-dotenv` | `.env` file loading |

Optional:

| Package | Purpose |
|---|---|
| `pyttsx3` | Offline TTS engine |
| `PyAudio` | Legacy microphone fallback |

---

## 🛠️ Troubleshooting

**No audio output on Linux?**
```bash
sudo apt install mpg123
```

**Microphone not detected?**
Make sure your default system microphone is set. On Linux, check `pavucontrol`.

**`recognize_google` failing?**
This requires internet access. Check your connection or switch to an offline STT engine.

**pyttsx3 not working on Python 3.12+?**
Use the default `gtts` engine instead, or install a compatible fork.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">Made with ❤️ — Talk to your machine, not at it.</p>
