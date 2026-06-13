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

# 🌐 Real-Time Web Search (Improved)
def internet_search(query):
    if not query or len(query.strip()) < 3:
        return ""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        print(f"Search Error: {e}")
    return "No fresh internet data available right now."

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)

    if not user_message and not image_base64:
        return jsonify({"error": "Message or image required"}), 400

    # 🔥 ALWAYS Do Real-Time Search
    search_query = user_message if user_message else "current events"
    search_context = internet_search(search_query)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Strong Real-Time Instruction
    base_instruction = (
        "You are Mehta AI, a highly accurate and updated assistant in 2026. "
        "You MUST use the latest real-time internet data provided below. "
        "Ignore any knowledge older than the provided search results. "
        "Always prioritize the freshest facts. "
        "Respond in the same language as the user. Be detailed and truthful."
    )

    if image_base64:
        # Vision Mode (Free Model)
        selected_model = "google/gemma-4-26b-a4b-it:free"

        content = []
        if user_message:
            content.append({"type": "text", "text": user_message})
        else:
            content.append({"type": "text", "text": "Is image ko detail mein analyze karo."})

        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": content}
        ]

        # Add real-time context
        if search_context:
            messages.append({"role": "user", "content": f"[LIVE REAL-TIME INTERNET DATA 2026]:\n{search_context}"})

    else:
        # Text Only Mode
        selected_model = "deepseek/deepseek-chat"

        final_prompt = f"{base_instruction}\n\n[LIVE REAL-TIME DATA]:\n{search_context}\n\nUser Question: {user_message}"

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
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
        res_data = response.json()

        if 'error' in res_data:
            error_msg = res_data['error'].get('message', str(res_data['error']))
            return jsonify({"reply": f"Error: {error_msg}"})

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        return jsonify({"reply": clean_reply})

    except Exception as e:
        print("Backend Error:", str(e))
        return jsonify({"reply": "Server error, thodi der baad try karo."}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
