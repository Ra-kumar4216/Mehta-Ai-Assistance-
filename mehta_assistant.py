"""
╔══════════════════════════════════════════════════════════════════╗
║          MEHTA — Voice-Controlled AI Assistant                   ║
║          Powered by OpenRouter (DeepSeek) + pyttsx3/gTTS         ║
║          Python 3.14 Compatible Version                          ║
╚══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REQUIRED INSTALLATION (run these first):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pip install SpeechRecognition sounddevice soundfile numpy requests gTTS pygame

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HOW TO RUN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Set your OPENROUTER_API_KEY below (or as an environment variable).
  2. Run:  python mehta_assistant.py
  3. Speak when you hear the prompt. Say "exit" or "quit" to stop.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import re
import sys
import time
import logging
import tempfile
import platform
import subprocess
import webbrowser
import urllib.parse
import urllib.request
from pathlib import Path

# ──────────────────────────────────────────
#  CONFIGURABLE SETTINGS  ← edit these
# ──────────────────────────────────────────

OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "OPENROUTER_API_KEY")
OPENROUTER_MODEL    = "deepseek/deepseek-chat"          # free-tier DeepSeek on OpenRouter
OPENROUTER_URL      = "https://openrouter.ai/api/v1/chat/completions"

TTS_ENGINE          = "gtts"        # "pyttsx3" (offline) | "gtts" (online, needs internet)
TTS_LANGUAGE        = "en"          # used by gTTS; pyttsx3 uses system voices
TTS_RATE            = 170           # pyttsx3 words-per-minute (default ~200)
TTS_VOLUME          = 1.0           # 0.0 – 1.0

DOWNLOAD_FOLDER     = str(Path.home() / "Downloads" / "Mehta")   # all downloads go here
SAFETY_MODE         = True          # require confirmation for destructive actions
MAX_HISTORY_TURNS   = 10            # how many conversation turns to keep in context

WAKE_WORD           = None          # set to e.g. "hey mehta" to require wake word, or None
LISTEN_TIMEOUT      = 7             # seconds to wait for speech before giving up
PHRASE_TIME_LIMIT   = 15            # max seconds for a single phrase

SYSTEM_PROMPT = (
    "You are Mehta, a helpful, concise voice assistant. "
    "Keep responses short and natural — this will be spoken aloud. "
    "Avoid markdown, bullet points, code blocks, or special symbols. "
    "Never use asterisks, hashtags, backticks, or emojis. "
    "Speak in plain English sentences only."
)

# ──────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("Mehta")

# ──────────────────────────────────────────
#  LAZY IMPORTS  (with helpful error msgs)
# ──────────────────────────────────────────

def _require(package, pip_name=None):
    """Import a package, printing install hint on failure."""
    import importlib
    try:
        return importlib.import_module(package)
    except ImportError:
        pip_name = pip_name or package
        print(f"\n[ERROR] Missing package '{package}'. Install with:\n  pip install {pip_name}\n")
        sys.exit(1)

# ──────────────────────────────────────────
#  TEXT CLEANING  (critical for TTS)
# ──────────────────────────────────────────

_CODE_BLOCK   = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_INLINE_CODE  = re.compile(r"`[^`]*`")
_MARKDOWN_HDR = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_ITALIC  = re.compile(r"(\*{1,3}|_{1,3})(.*?)\1")
_LINKS        = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_HTML_TAGS    = re.compile(r"<[^>]+>")
_EMOJIS       = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE,
)
_SPECIAL_CHARS = re.compile(r"[*#~|\\^><={}\[\]]")
_MULTIPLE_SPACES = re.compile(r"  +")
_MULTIPLE_NEWLINES = re.compile(r"\n{2,}")


def clean_text(text: str) -> str:
    """
    Strip all markdown, emojis, code blocks, and special characters
    so the text is safe and natural for TTS.
    """
    if not text:
        return ""
    text = _CODE_BLOCK.sub(" ", text)
    text = _INLINE_CODE.sub(" ", text)
    text = _MARKDOWN_HDR.sub("", text)
    text = _BOLD_ITALIC.sub(r"\2", text)
    text = _LINKS.sub(r"\1", text)
    text = _HTML_TAGS.sub(" ", text)
    text = _EMOJIS.sub("", text)
    text = _SPECIAL_CHARS.sub("", text)
    text = text.replace("&amp;", "and")
    text = text.replace("&lt;", "less than")
    text = text.replace("&gt;", "greater than")
    text = text.replace("\t", " ")
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_NEWLINES.sub(". ", text)
    text = text.strip()
    return text


# ──────────────────────────────────────────
#  SPEECH-TO-TEXT  (listen)
#  Uses sounddevice instead of pyaudio
#  — works on Python 3.14
# ──────────────────────────────────────────

def listen(prompt: str = "Listening…") -> str | None:
    """
    Capture microphone input and return recognised text (lowercase).
    Returns None on silence, timeout, or unrecognised speech.
    Uses sounddevice backend (Python 3.14 compatible).
    """
    try:
        import speech_recognition as sr
        import sounddevice as sd
        import numpy as np
    except ImportError:
        print("\n[ERROR] Install: pip install SpeechRecognition sounddevice soundfile numpy\n")
        sys.exit(1)

    recognizer = sr.Recognizer()
    print(f"\n🎙  {prompt}")

    # Use sounddevice as the audio source via a responsive chunk-by-chunk capture
    try:
        sample_rate = 16000
        chunk_size = 1024

        # Automatically calibrate silence threshold from ambient noise
        print("   (Adjusting for ambient noise...)")
        bg_noise = sd.rec(int(sample_rate * 0.3), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        bg_energy = np.percentile(np.abs(bg_noise), 95)
        # Set threshold slightly above background noise
        threshold = max(int(bg_energy * 1.5), 150)

        audio_chunks = []
        speaking = False
        silence_chunks = 0
        max_silence_chunks = int(1.2 * sample_rate / chunk_size)  # 1.2s silence to stop
        start_time = time.time()

        print("   (Speak now...)")
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_size) as stream:
            while True:
                data, overflowed = stream.read(chunk_size)
                audio_chunks.append(data.copy())
                
                # Check amplitude of chunk
                energy = np.max(np.abs(data))
                
                if energy > threshold:
                    if not speaking:
                        speaking = True
                    silence_chunks = 0
                else:
                    if speaking:
                        silence_chunks += 1
                        if silence_chunks > max_silence_chunks:
                            break
                
                # Timeout safety
                elapsed = time.time() - start_time
                if elapsed > PHRASE_TIME_LIMIT:
                    break
                if not speaking and elapsed > LISTEN_TIMEOUT:
                    # User did not start speaking
                    return None

        if not audio_chunks:
            return None

        audio_np = np.concatenate(audio_chunks, axis=0).flatten()
        audio_bytes = audio_np.tobytes()
        audio_sr = sr.AudioData(audio_bytes, sample_rate, 2)  # 2 bytes per sample (int16)

        text = recognizer.recognize_google(audio_sr, language="en-US")
        log.info(f"You said: {text}")
        return text.lower().strip()

    except Exception as e:
        log.debug(f"sounddevice listen error: {e}")

    # Fallback: try standard sr.Microphone (may work if pyaudio available)
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                )
            except sr.WaitTimeoutError:
                log.debug("Listen timeout — no speech detected.")
                return None

        text = recognizer.recognize_google(audio, language="en-US")
        log.info(f"You said: {text}")
        return text.lower().strip()

    except Exception as e2:
        log.warning(f"STT error: {e2}")
        return None


# ──────────────────────────────────────────
#  TEXT-TO-SPEECH  (speak)
# ──────────────────────────────────────────

def _speak_pyttsx3(text: str):
    pyttsx3 = _require("pyttsx3")
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", TTS_RATE)
        engine.setProperty("volume", TTS_VOLUME)
        voices = engine.getProperty("voices")
        for v in voices:
            if "english" in v.name.lower() or "en" in (v.languages[0] if v.languages else ""):
                engine.setProperty("voice", v.id)
                break
        engine.say(text)
        engine.runAndWait()
        del engine
    except Exception as e:
        log.warning(f"pyttsx3 speak failed: {e}")


def _speak_gtts(text: str):
    gtts_mod  = _require("gtts", "gTTS")
    gTTS = gtts_mod.gTTS

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        tts = gTTS(text=text, lang=TTS_LANGUAGE)
        tts.save(tmp_path)
        _play_audio(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _play_audio(path: str):
    """Cross-platform audio playback — native Windows MCI for MP3/WAV."""
    import platform
    import subprocess
    import ctypes

    system = platform.system()
    if system == "Windows":
        try:
            path_abs = os.path.abspath(path)
            # Get short path name to avoid spaces/quotes issues with MCI command string
            buf = ctypes.create_unicode_buffer(300)
            ctypes.windll.kernel32.GetShortPathNameW(path_abs, buf, 300)
            short_path = buf.value
            
            ctypes.windll.winmm.mciSendStringW(f'open "{short_path}" type mpegvideo alias tts_audio', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW('play tts_audio wait', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW('close tts_audio', None, 0, 0)
            return
        except Exception as e:
            log.debug(f"Windows MCI playback failed: {e}")
            pass

    # OS-level fallback for other systems
    if system == "Darwin":
        subprocess.call(["afplay", path])
    elif system == "Linux":
        subprocess.call(["mpg123", "-q", path])


def speak(text: str):
    """Clean and speak the given text aloud."""
    clean = clean_text(text)
    if not clean:
        return
    print(f"\n🔊 Mehta: {clean}\n")
    try:
        if TTS_ENGINE == "gtts":
            _speak_gtts(clean)
        else:
            _speak_pyttsx3(clean)
    except Exception as e:
        log.warning(f"TTS failed ({e}); text printed above.")


# ──────────────────────────────────────────
#  LLM VIA OPENROUTER  (generate_reply)
# ──────────────────────────────────────────

_conversation_history: list[dict] = []


def generate_reply(user_text: str) -> str:
    """
    Send user_text to OpenRouter (DeepSeek) and return the assistant reply.
    Maintains a rolling conversation history.
    """
    import json

    _conversation_history.append({"role": "user", "content": user_text})

    trimmed = _conversation_history[-(MAX_HISTORY_TURNS * 2):]

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + trimmed,
        "max_tokens": 512,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/mehta-assistant",
        "X-Title": "Mehta Voice Assistant",
    }

    try:
        import requests
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        _conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        log.error(f"LLM error: {e}")
        return "Sorry, I could not reach the AI service right now."


# ──────────────────────────────────────────
#  COMMAND PARSER  (intent detection)
# ──────────────────────────────────────────

COMMAND_PATTERNS = {
    "shutdown":       r"\b(shutdown|shut down|power off|turn off (the )?(computer|pc|laptop))\b",
    "restart":        r"\b(restart|reboot|boot again)\b",
    "open_website":   r"\b(open|go to|visit|navigate to|launch)\s+(?:the\s+)?(?:website\s+)?(.+)",
    "google_search":  r"\b(search|google|look up|find)\s+(?:for\s+)?(.+)",
    "download_file":  r"\b(download)\s+(.+?)\s+from\s+(https?://\S+)",
    "open_file":      r"\b(open|launch|run)\s+(.+\.\w{2,5})\b",
    "list_files":     r"\b(list|show|what('?s| is) in)\s+(files|folder|directory)\b",
    "create_folder":  r"\b(create|make|new)\s+folder\s+(.+)",
    "delete_file":    r"\b(delete|remove)\s+(.+)",
    "exit":           r"\b(exit|quit|bye|goodbye|stop listening|shut up)\b",
}

_compiled_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in COMMAND_PATTERNS.items()}


def parse_command(text: str) -> tuple[str, list[str]] | None:
    for intent, pattern in _compiled_patterns.items():
        m = pattern.search(text)
        if m:
            return intent, list(m.groups())
    return None


def confirm(prompt: str) -> bool:
    """Speak a yes/no confirmation prompt and return True if user says yes."""
    speak(prompt + " Say yes to confirm or no to cancel.")
    response = listen("Waiting for your confirmation…")
    if response and re.search(r"\byes\b", response, re.IGNORECASE):
        return True
    speak("Action cancelled.")
    return False


# ──────────────────────────────────────────
#  PC CONTROL  (perform_action)
# ──────────────────────────────────────────

def perform_action(intent: str, groups: list[str]) -> str | None:
    system = platform.system()

    if intent == "exit":
        speak("Goodbye! Have a great day.")
        sys.exit(0)

    if intent == "shutdown":
        if SAFETY_MODE and not confirm("Are you sure you want to shut down the computer?"):
            return "Shutdown cancelled."
        speak("Shutting down now.")
        if system == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "5"])
        else:
            subprocess.run(["shutdown", "-h", "now"])
        return "Initiating shutdown."

    if intent == "restart":
        if SAFETY_MODE and not confirm("Are you sure you want to restart the computer?"):
            return "Restart cancelled."
        speak("Restarting now.")
        if system == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "5"])
        else:
            subprocess.run(["shutdown", "-r", "now"])
        return "Initiating restart."

    if intent == "open_website":
        site = groups[-1].strip()
        if not site.startswith("http"):
            site_clean = site.replace(" ", "")
            if "." not in site_clean:
                site_clean += ".com"
            url = "https://" + site_clean
        else:
            url = site
        log.info(f"Opening URL: {url}")
        webbrowser.open(url)
        return f"Opening {site} in your browser."

    if intent == "google_search":
        query = groups[-1].strip()
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        log.info(f"Searching Google: {query}")
        webbrowser.open(url)
        return f"Searching Google for {query}."

    if intent == "download_file":
        _, description, url = groups[0], groups[1], groups[2]
        url = url.strip()
        folder = Path(DOWNLOAD_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)
        filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
        dest = folder / filename

        if SAFETY_MODE and not confirm(f"Download {filename} to {folder}?"):
            return "Download cancelled."

        speak(f"Downloading {filename}, please wait.")
        try:
            urllib.request.urlretrieve(url, dest)
            return f"Downloaded {filename} to {folder}."
        except Exception as e:
            log.error(f"Download failed: {e}")
            return f"Download failed. {e}"

    if intent == "open_file":
        filepath = groups[-1].strip()
        path = Path(filepath).expanduser()
        if not path.exists():
            return f"I could not find the file {filepath}."
        log.info(f"Opening file: {path}")
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
        return f"Opening {path.name}."

    if intent == "list_files":
        folder = Path(DOWNLOAD_FOLDER)
        if not folder.exists():
            return f"The folder {folder} does not exist yet."
        files = [f.name for f in folder.iterdir() if f.is_file()]
        if not files:
            return "The downloads folder is empty."
        names = ", ".join(files[:10])
        suffix = f" and {len(files) - 10} more" if len(files) > 10 else ""
        return f"Files in your downloads folder: {names}{suffix}."

    if intent == "create_folder":
        folder_name = groups[-1].strip()
        new_folder = Path(DOWNLOAD_FOLDER) / folder_name
        new_folder.mkdir(parents=True, exist_ok=True)
        return f"Folder {folder_name} created inside your downloads folder."

    if intent == "delete_file":
        filename = groups[-1].strip()
        target = Path(DOWNLOAD_FOLDER) / filename
        if not target.exists():
            return f"I could not find {filename} in the downloads folder."
        if SAFETY_MODE and not confirm(f"Permanently delete {filename}?"):
            return "Deletion cancelled."
        try:
            target.unlink()
            return f"Deleted {filename}."
        except Exception as e:
            return f"Could not delete the file. {e}"

    return None


# ──────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────

def main():
    log.info("Mehta Assistant starting…")

    if OPENROUTER_API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️  Please set your OPENROUTER_API_KEY in the script or as an environment variable.\n")
        sys.exit(1)

    Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

    speak("Hello! I'm Mehta, your voice assistant. How can I help you today?")

    while True:
        try:
            if WAKE_WORD:
                raw = listen(f"Say '{WAKE_WORD}' to activate…")
                if not raw or WAKE_WORD not in raw:
                    continue

            user_input = listen("Listening — speak now…")
            if not user_input:
                speak("I didn't catch that. Please try again.")
                continue

            if re.search(r"\b(exit|quit|goodbye|bye)\b", user_input, re.IGNORECASE):
                speak("Goodbye! Have a great day.")
                break

            result = parse_command(user_input)
            if result:
                intent, groups = result
                response = perform_action(intent, groups)
                if response:
                    speak(response)
                    continue

            speak("Let me think…")
            reply = generate_reply(user_input)
            speak(reply)

        except KeyboardInterrupt:
            speak("Interrupted. Goodbye!")
            break
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            speak("Something went wrong. Please try again.")


# ──────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────

if __name__ == "__main__":
    main()