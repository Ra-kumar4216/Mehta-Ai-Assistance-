from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def internet_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except:
        pass
    return ""

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)

    if not user_message and not image_base64:
        return jsonify({"error": "Message or image required"}), 400

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    base_instruction = "You are Mehta AI, a helpful and smart assistant. Respond in the same language as the user."

    if image_base64:
        selected_model = "google/gemma-4-26b-a4b-it:free"   # ← Best free vision

        content = [{"type": "text", "text": user_message or "Is image ko detail mein analyze karo."}]
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": content}
        ]
    else:
        selected_model = "deepseek/deepseek-chat"
        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": user_message}
        ]

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
        res_data = response.json()

        if 'error' in res_data:
            error_msg = res_data['error'].get('message', str(res_data['error']))
            return jsonify({"reply": f"Error: {error_msg}"})

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        return jsonify({"reply": clean_reply})

    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
