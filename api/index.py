from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
from duckduckgo_search import DDGS
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    
    current_year = datetime.now().year

    try:
        with DDGS() as ddgs:
            results = []
            search_queries = [
                f"{query} {current_year}",
                f"{query} latest"
            ]
            for q in search_queries:
                try:
                    res = list(ddgs.text(q, max_results=4))
                    results.extend(res)
                except Exception:
                    continue

            if results:
                unique_results = []
                seen = set()
                for r in results:
                    title = r.get('title', '').strip()
                    body = r.get('body', '').strip()
                    url = r.get('href', '')
                    if title and title not in seen and body:
                        seen.add(title)
                        unique_results.append(f"• {title}: {body}\n  Source: {url}")

                if unique_results:
                    timestamp = datetime.now().strftime("%d %B %Y, %H:%M UTC")
                    return f"[Fetched: {timestamp}]\n" + "\n".join(unique_results[:6])

    except Exception as e:
        print(f"Search Error: {e}")

    return ""


def build_messages(user_message, search_context, history, image_base64):
    base_instruction = (
        "You are Mehta AI, a smart and friendly assistant for the year 2026. "
        "Always use the real-time internet data provided to give accurate, up-to-date answers. "
        "If search results contain relevant info, use them confidently — do not say 'I don't know' if data is present. "
        "Respond in the same language the user writes in (Hindi, English, or Hinglish). "
        "Be concise, clear, and helpful."
    )

    messages = [{"role": "system", "content": base_instruction}]

    if history:
        trimmed = history[-12:]
        for h in trimmed:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    if search_context:
        messages.append({
            "role": "system",
            "content": f"[REAL-TIME INTERNET DATA]\n{search_context}"
        })

    if image_base64:
        content = [{"type": "text", "text": user_message or "Is image ko analyze karo."}]
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_message})

    return messages


@app.route('/api/chat', methods=['POST'])
def chat():
    if not OPENROUTER_API_KEY:
        return jsonify({
            "error": "OPENROUTER_API_KEY not set. Please add it in Vercel Environment Variables or .env file."
        }), 500

    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)
    history = data.get("history", [])

    if not user_message and not image_base64:
        return jsonify({"error": "Message or image required"}), 400

    search_context = internet_search(user_message) if user_message else ""

    selected_model = "google/gemma-3-27b-it:free" if image_base64 else "deepseek/deepseek-chat"

    messages = build_messages(user_message, search_context, history, image_base64)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://mehta-ai.vercel.app",
        "X-Title": "Mehta AI Assistant"
    }

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1024
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        if 'error' in res_data:
            err_msg = res_data['error'].get('message', 'Unknown API error')
            return jsonify({"error": f"AI Error: {err_msg}"}), 502

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()

        return jsonify({
            "reply": clean_reply,
            "model_used": selected_model,
            "search_used": bool(search_context)
        })

    except requests.Timeout:
        return jsonify({"error": "Request timed out. Please try again."}), 504
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(OPENROUTER_API_KEY),
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
