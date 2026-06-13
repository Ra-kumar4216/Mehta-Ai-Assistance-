import os
import base64
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 🔥 Light-Weight & Direct Internet Search
def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            links = re.findall(r'<a class="result__snippet"[\s\S]*?>([\s\S]*?)</a>', html)
            titles = re.findall(r'<a class="result__url"[\s\S]*?>([\s\S]*?)</a>', html)
            
            unique_results = []
            for i in range(min(len(links), 5)):
                clean_title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                clean_desc = re.sub(r'<[^>]+>', '', links[i]).strip()
                if clean_title and clean_desc:
                    unique_results.append(f"• {clean_title}: {clean_desc}")
            
            if unique_results:
                return "\n".join(unique_results)
    except Exception as e:
        print(f"Search Error: {e}")
    return ""

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        image_data_url = data.get("image", None)
        
        if not user_message and not image_data_url:
            return jsonify({"error": "Message or image required"}), 400
            
        search_context = ""
        # सिर्फ तभी सर्च करें जब इमेज न हो या कोई विशिष्ट टेक्स्ट पूछा गया हो
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        # 🌟 सिस्टम इंस्ट्रक्शन को मॉडल के अंदर सही तरीके से सेट कर रहे हैं
        base_instruction = (
            "You are Mehta AI, a highly accurate and updated assistant for 2026. "
            "If the user uploads an image, priority must be given to analyzing and identifying the image content. "
            "Respond directly, confidently, and clearly in the same language as the user."
        )
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=base_instruction
        )
        
        content_parts = []
        
        # 1. अगर इमेज है, तो उसे सबसे पहले जोड़ें
        if image_data_url and "," in image_data_url:
            header, encoded = image_data_url.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            
            content_parts.append({
                "mime_type": mime_type,
                "data": image_bytes
            })
            
        # 2. यूज़र का टेक्स्ट या सर्च कॉन्टेक्स्ट जोड़ें
        if search_context:
            content_parts.append(f"[REAL-TIME INTERNET DATA]:\n{search_context}\n\nUser Question: {user_message}")
        elif user_message:
            content_parts.append(user_message)
        else:
            content_parts.append("Is image ko dekho aur batao ye kya hai ya kaun hai.")
            
        # Gemini से रिस्पॉन्स लें
        response = model.generate_content(content_parts)
        
        reply = response.text
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        
        return jsonify({"reply": clean_reply})
        
    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
