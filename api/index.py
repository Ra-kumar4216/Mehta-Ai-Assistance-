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

# 🎯 AI Query Optimizer Function
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
                "content": "You are a precise search query optimizer. Convert the user's input into a single, clean English search engine query. Respond ONLY with plain text keywords."
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
    image_base64 = data.get("image", None)  # 📸 Frontend se image lena
    
    if not user_message and not image_base64:
        return jsonify({"error": "No message or image provided"}), 400

    search_context = ""
    if user_message and not image_base64:
        live_keywords = ["latest", "today", "news", "current", "weather", "search", "aaj ka", "batao", "dhundho", "price", "padha", "kaha se", "kaun hai", "who is", "where"]
        if any(keyword in user_message.lower() for keyword in live_keywords):
            search_query = optimize_search_query(user_message)
            search_context = internet_search(search_query)

    # 🎯 Instructions
    base_instruction = "You are Mehta AI Assistant, a smart, accurate and helpful AI. Provide responses in the same language or script used by the user."
    if search_context:
        base_instruction += f"\n\n[CRITICAL LIVE INTERNET CONTEXT]:\n{search_context}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # 👁️ OpenRouter Multi-modal / Vision Pattern Fix
    if image_base64:
        # 📸 IMAGE CASE: Vision ke liye standard Google Gemini Flash model best aur hamesha live hai
        selected_model = "google/gemini-2.5-flash:free"
        prompt_text = f"{base_instruction}\n\nUser Question: {user_message if user_message else 'Analyze this image thoroughly and tell me what it is.'}"
        
        payload = {
            "model": selected_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }
    else:
        # 💬 NORMAL TEXT CASE (DeepSeek)
        selected_model = "deepseek/deepseek-chat"
        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": base_instruction},
                {"role": "user", "content": user_message}
            ]
        }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        res_data = response.json()
        
        # 🚨 SAFE PARSING: Agar OpenRouter API koi error bhejti hai toh server crash nahi hoga, screen par error dikhega
        if 'error' in res_data:
            return jsonify({"reply": f"OpenRouter Error: {res_data['error'].get('message', 'Unknown Error')}"})
            
        if 'choices' in res_data and len(res_data['choices']) > 0:
            reply = res_data['choices'][0]['message']['content']
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "Unexpected response structure from OpenRouter server. Please try again."})
            
    except Exception as e:
        return jsonify({"reply": f"Backend Error: {str(e)}"}), 500
