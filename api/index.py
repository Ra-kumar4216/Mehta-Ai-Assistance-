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

    base_instruction = "You are Mehta AI, a helpful assistant. Respond in the user's language."

    if image_base64:
        selected_model = "qwen/qwen2.5-vl-32b-instruct:free"   # ← Best working free vision

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
            {"role": "user", "content": f"{user_message}\n\nSearch context: {internet_search(user_message)}"}
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

        # Better Error Logging
        if 'error' in res_data:
            error_detail = res_data['error']
            print("OpenRouter Error:", error_detail)  # ← Yeh Vercel logs mein dikhega
            return jsonify({"reply": f"Error: {error_detail.get('message', str(error_detail))}"})

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        return jsonify({"reply": clean_reply})

    except Exception as e:
        print("Backend Exception:", str(e))
        return jsonify({"reply": "Server error, thodi der baad try karo."}), 500
