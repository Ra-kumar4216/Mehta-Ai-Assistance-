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

# 🌐 Real-Time Web Search
def internet_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except:
        pass
    return ""

# Search Optimizer
def optimize_search_query(user_msg):
    # Simple fallback for free
    return user_msg[:200] if user_msg else "latest news"

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)

    if not user_message and not image_base64:
        return jsonify({"error": "Message or image required"}), 400

    search_context = internet_search(user_message) if user_message else ""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    base_instruction = (
        "You are Mehta AI, a helpful and intelligent assistant. "
        "Respond in the same language as the user. Be detailed and accurate."
    )

    # ==================== FREE VISION SETUP ====================
    if image_base64:
        # Free Vision Model
        selected_model = "google/gemma-4-31b-it:free"   # Best free vision right now
        
        content = []
        
        if user_message:
            content.append({"type": "text", "text": user_message})
        else:
            content.append({"type": "text", "text": "Is image ko bahut detail mein analyze karo. Sab kuch describe karo."})
        
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": content}
        ]

        if search_context:
            messages.append({"role": "user", "content": f"[Live Internet Context]:\n{search_context}"})

    else:
        # Normal Text Chat (Free Model)
        selected_model = "deepseek/deepseek-chat"   # Ya "qwen/qwen2.5-coder-32b-instruct:free"
        
        final_prompt = f"{base_instruction}\n\n{search_context}\n\nUser: {user_message}"
        
        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": final_prompt}
        ]

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        if 'error' in res_data:
            return jsonify({"reply": f"Error: {res_data['error'].get('message', 'Unknown error')}"})

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        
        return jsonify({"reply": clean_reply})

    except Exception as e:
        return jsonify({"reply": f"Backend Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
