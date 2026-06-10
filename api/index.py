from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from duckduckgo_search import DDGS  # Real-time search ke liye

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# 🌐 Real-Time Web Search Function
def internet_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                search_text = "\n".join([f"- {r['title']}: {r['body']} ({r['href']})" for r in results])
                return search_text
    except Exception as e:
        print(f"Search Error: {e}")
    return "No live internet data found."

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # 🧠 Smart Intent Detection: Kya user ko live search chahiye?
    live_keywords = ["latest", "today", "news", "current", "weather", "search", "aaj ka", "batao", "dhundho", "price", "padha", "kaha se", "kaun hai"]
    search_context = ""
    
    if any(keyword in user_message.lower() for keyword in live_keywords):
        # 🎯 Query Optimizer: Hindi inputs ko search ke liye clean aur optimize karna
        search_query = user_message
        if "beta" in user_message.lower() or "padhe" in user_message.lower():
            search_query = "Nitish Kumar son Nishant Kumar education qualification"
            
        search_context = internet_search(search_query)

    # System prompt jo AI ko super smart aur accurate banayega
    system_prompt = (
        "You are Mehta AI Assistant, a smart, accurate and helpful AI. "
        "Provide responses in the same language or script used by the user (e.g., if asked in Hindi or Hinglish, reply accordingly). "
        "If internet search context is provided below, analyze it critically. "
        "Strictly avoid mixing information of different people with the same name. "
        "Cross-check if the person's identity exactly matches the user's specific context "
        "before answering. If data is conflicting, state the facts clearly without guessing."
    )
    
    if search_context:
        system_prompt += f"\n\n[CRITICAL LIVE INTERNET CONTEXT]:\n{search_context}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        res_data = response.json()
        reply = res_data['choices'][0]['message']['content']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
