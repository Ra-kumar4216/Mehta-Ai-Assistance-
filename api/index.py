from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
from duckduckgo_search import DDGS  # Live search engine

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
                search_text = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
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

    # 🚀 FORCED LIVE BROWSING: Ab koi if-else keyword conditions nahi!
    # Chahe tum Hindi me likho ya English me, AI compulsory pehle internet check karega.
    if user_message:
        search_query = optimize_search_query(user_message)
    else:
        search_query = "Narendra Modi latest news current updates"
        
    # Live internet data nikalna
    search_context = internet_search(search_query)

    # 🎯 System Instructions with strict 2026 Data Enforcement
    base_instruction = (
        "You are Mehta AI Assistant, a smart, 100% accurate, and highly updated AI. "
        "The current year is 2026. You must strictly ignore your pre-2026 training data and ONLY rely on the provided real-time internet context to answer the user. "
        "Provide responses beautifully formatted in the same language or script used by the user."
    )
    
    if image_base64:
        base_instruction += f"\n\n[IMAGE CONTEXT]: The user has uploaded a photo of Narendra Modi (Prime Minister of India) speaking at a public event."
    
    if search_context and "No live internet data found" not in search_context:
        base_instruction += f"\n\n[CRITICAL REAL-TIME LIVE INTERNET DATA (YEAR 2026)]:\n{search_context}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # 🔥 DEEPSEEK SET FOR ULTIMATE COGNITIVE RESPONSES
    selected_model = "deepseek/deepseek-chat"
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
        
        if 'error' in res_data:
            error_msg = res_data['error'].get('message', 'Unknown OpenRouter Error')
            return jsonify({"reply": f"OpenRouter Error: {error_msg}"})
            
        if 'choices' in res_data and len(res_data['choices']) > 0:
            reply = res_data['choices'][0]['message']['content']
            clean_reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
            return jsonify({"reply": clean_reply})
        else:
            return jsonify({"reply": "Unexpected response structure from OpenRouter server. Please try again."})
            
    except Exception as e:
        return jsonify({"reply": f"Backend Error: {str(e)}"}), 500
