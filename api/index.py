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
        
        clean_query = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        clean_query = clean_query.replace('"', '').replace("'", "").replace('{', '').replace('}', '')
        return clean_query if clean_query else user_msg
    except Exception as e:
        print(f"Optimization Error: {e}")
        return user_msg

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    image_base64 = data.get("image", None)  # 📸 Frontened se image data lena
    
    if not user_message and not image_base64:
        return jsonify({"error": "No message or image provided"}), 400

    search_context = ""
    
    if user_message and not image_base64:
        live_keywords = ["latest", "today", "news", "current", "weather", "search", "aaj ka", "batao", "dhundho", "price", "padha", "kaha se", "kaun hai", "who is", "where", "qualify"]
        if any(keyword in user_message.lower() for keyword in live_keywords):
            search_query = optimize_search_query(user_message)
            search_context = internet_search(search_query)

    system_prompt = (
        "You are Mehta AI Assistant, a smart, accurate and helpful AI. "
        "Provide responses in the same language or script used by the user. "
        "If an image is provided, analyze it thoroughly and answer the user's question about it accurately."
    )
    
    if search_context:
        system_prompt += f"\n\n[CRITICAL LIVE INTERNET CONTEXT]:\n{search_context}"

    # 👁️ Vision Payload Structure
    user_content = []
    if user_message:
        user_content.append({"type": "text", "text": user_message})
    
    if image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        })

    # 🎯 Model Selection: Image ke liye Gemini Vision, normal ke liye DeepSeek
    selected_model = "google/gemini-2.5-flash:free" if image_base64 else "deepseek/deepseek-chat"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
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
