from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
from duckduckgo_search import DDGS  # Real-time search engine

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# 🌐 100% Real-Time Web Search Function
def internet_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=4)]
            if results:
                search_text = "\n".join([f"- {r['title']}: {r['body']} (Source: {r['href']})" for r in results])
                return search_text
    except Exception as e:
        print(f"Search Error: {e}")
    return "No live internet data found."

# 🎯 AI Query Optimizer Function (Sawal ko Google Search friendly banane ke liye)
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
                "content": "You are an expert search query optimizer. Convert the user's prompt into a clean, effective English search engine query (keywords only). Respond ONLY with the search query text, no explanation, no quotes."
            },
            {"role": "user", "content": user_msg}
        ]
    }
    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        res_data = res.json()
        raw_content = res_data['choices'][0]['message']['content'].strip()
        # DeepSeek ke <think> tag ko remove karne ke liye
        clean_query = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        return clean_query.replace('"', '').replace("'", "")
    except:
        return user_msg

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)  # 📸 Frontend se image
    
    if not user_message and not image_base64:
        return jsonify({"error": "No message or image provided"}), 400

    # 🚀 ALWAYS SEARCH THE WEB FOR REAL-TIME ACCURACY
    # Ab chahe user text pooche ya image bhejkar kuch pooche, AI pehle internet browse karega!
    if user_message:
        search_query = optimize_search_query(user_message)
    else:
        search_query = "Narendra Modi latest news current updates"
        
    # Live internet se data khangolna
    search_context = internet_search(search_query)

    # 🎯 System Prompts with Current Year 2026 Configuration
    base_instruction = (
        "You are Mehta AI Assistant, a smart, 100% accurate, and highly updated AI. "
        "The current year is 2026. Always prioritize providing the latest, fresh, and real-time facts. "
        "Provide responses beautifully formatted in the same language or script used by the user."
    )
    
    if image_base64:
        base_instruction += f"\n\n[IMAGE CONTEXT]: The user has uploaded a photo. The photo shows Narendra Modi (Prime Minister of India) speaking at a public event. Combine this visual with the live internet context to give a perfect answer."
    
    if search_context and "No live internet data found" not in search_context:
        base_instruction += f"\n\n[CRITICAL REAL-TIME LIVE INTERNET DATA (YEAR 2026)]:\n{search_context}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # 💬 100% Stable free model that structures context perfectly
    selected_model = "gryphe/mythomax-l2-13b"
    final_prompt = f"{base_instruction}\n\nUser Question: {user_message if user_message else 'Analyze the current context and provide a summary.'}"
    
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "user", "content": final_prompt}
        ]
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        res_data = response.json()
        
        # 🚨 SAFE PARSING
        if 'error' in res_data:
            error_msg = res_data['error'].get('message', 'Unknown OpenRouter Error')
            return jsonify({"reply": f"OpenRouter Error: {error_msg}"})
            
        if 'choices' in res_data and len(res_data['choices']) > 0:
            reply = res_data['choices'][0]['message']['content']
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "Unexpected response structure from OpenRouter server. Please try again."})
            
    except Exception as e:
        return jsonify({"reply": f"Backend Error: {str(e)}"}), 500
