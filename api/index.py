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

# 🔥 Super Improved Real-Time Search
def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    try:
        with DDGS() as ddgs:
            results = []
            # Multiple strong queries
            search_queries = [
                query,
                f"{query} 2026",
                f"current {query}",
                f"who is the current {query}",
                f"{query} latest news"
            ]
            
            for q in search_queries:
                try:
                    res = list(ddgs.text(q, max_results=5))
                    results.extend(res)
                except:
                    continue
                    
            if results:
                unique_results = []
                seen = set()
                for r in results:
                    title = r.get('title', '').strip()
                    body = r.get('body', '').strip()
                    if title and title not in seen and body:
                        seen.add(title)
                        unique_results.append(f"• {title}: {body}")
                return "\n".join(unique_results[:8])
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

    # Strong Real-Time Search
    search_context = internet_search(user_message)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Very Strong Instruction for Real-Time Data
    base_instruction = (
        "You are Mehta AI, a highly accurate and updated assistant for 2026. "
        "You MUST always use the latest real-time internet data provided in the context. "
        "Never say 'no fresh data' or 'information not available' if any relevant information is present. "
        "Give direct, confident, and clear answers using the provided search results. "
        "Respond in the same language as the user."
    )

    if image_base64:
        selected_model = "google/gemma-4-26b-a4b-it:free"
        content = [{"type": "text", "text": user_message or "Is image ko detail mein analyze karo."}]
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": content}
        ]
        if search_context:
            messages.append({"role": "user", "content": f"[REAL-TIME INTERNET DATA - JUNE 2026]:\n{search_context}"})
    else:
        selected_model = "deepseek/deepseek-chat"
        final_prompt = f"{base_instruction}\n\n[REAL-TIME INTERNET DATA - JUNE 2026]:\n{search_context}\n\nUser Question: {user_message}"

        messages = [
            {"role": "system", "content": base_instruction},
            {"role": "user", "content": final_prompt}
        ]

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.5,      # Lower temperature = more factual
        "max_tokens": 2048
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
        res_data = response.json()

        if 'error' in res_data:
            return jsonify({"reply": f"Error: {res_data['error'].get('message', 'Unknown')}"})

        reply = res_data['choices'][0]['message']['content']
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        return jsonify({"reply": clean_reply})

    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
