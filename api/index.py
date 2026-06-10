from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
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

# 🎯 AI Query Optimizer Function: Yeh har tarah ke sawal ko perfect search term banayega
def optimize_search_query(user_msg):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are a precise search query optimizer. Convert the user's input (regardless of letter casing, typos, or language like Hindi/Hinglish) into a single, clean English search engine query focused on fetching factual data. Respond ONLY with the plain text search keywords. Never use markdown, never wrap in JSON, and do not include any conversational filler."
            },
            {"role": "user", "content": user_msg}
        ]
    }
    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        res_data = res.json()
        raw_content = res_data['choices'][0]['message']['content'].strip()
        
        # 🧼 Filter: Agar DeepSeek reasoning/thinking tags <think>...</think> bhejta hai, toh use hatayein
        clean_query = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        
        # Faltu ke quotes aur brackets saaf karna
        clean_query = clean_query.replace('"', '').replace("'", "").replace('{', '').replace('}', '')
        return clean_query if clean_query else user_msg
    except Exception as e:
        print(f"Optimization Error: {e}")
        return user_msg  # Fallback agar AI fail ho jaye

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # 🧠 Super Smart Intent Detection (Har possible context keyword shamil hai)
    live_keywords = ["latest", "today", "news", "current", "weather", "search", "aaj ka", "batao", "dhundho", "price", "padha", "kaha se", "kaun hai", "who is", "where", "qualify"]
    search_context = ""
    
    if any(keyword in user_message.lower() for keyword in live_keywords):
        # Ab chahe lowercase ho ya uppercase, AI khud best search term banayega
        search_query = optimize_search_query(user_message)
        print(f"Optimized Search Query: {search_query}")
        search_context = internet_search(search_query)

    # System prompt jo AI ko super smart aur accurate banayega
    system_prompt = (
        "You are Mehta AI Assistant, a smart, accurate and helpful AI. "
        "Provide responses in the same language or script used by the user (e.g., if asked in Hindi or Hinglish, reply accordingly). "
        "If internet search context is provided below, analyze it critically. "
        "Strictly avoid mixing information of different people with the same name. "
        "Cross-check if the person's identity exactly matches the user's specific context "
        "before answering. If data is conflicting or not found, state the facts clearly without guessing."
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
        
        if 'choices' in res_data:
            reply = res_data['choices'][0]['message']['content']
            return jsonify({"reply": reply})
        else:
            return jsonify({"error": "Unexpected response structure from OpenRouter", "details": res_data}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
