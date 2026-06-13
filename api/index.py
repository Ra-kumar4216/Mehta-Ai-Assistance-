import os
import base64
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Frontend से बिना किसी CORS एरर के कनेक्ट करने के लिए

# Vercel पर सेट की हुई GEMINI_API_KEY को कॉन्फ़िगर करें
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 🔥 Light-Weight & Direct Internet Search (No external duckduckgo library needed)
def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    try:
        # सीधे DuckDuckGo के HTML एंडपॉइंट पर रिक्वेस्ट भेज रहे हैं जिससे Vercel क्रैश नहीं होगा
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            # HTML से सर्च रिज़ल्ट्स निकालने का आसान तरीका
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
    
    return "No fresh internet data available right now."

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        image_data_url = data.get("image", None)  # Frontend से आने वाली Base64 इमेज
        
        if not user_message and not image_data_url:
            return jsonify({"error": "Message or image required"}), 400
            
        # 1. इंटरनेट सर्च चलाएं (अगर यूजर ने टेक्स्ट पूछा है)
        search_context = ""
        if user_message:
            search_context = internet_search(user_message)
            
        # Gemini 2.5 Flash मॉडल लोड करें (टेक्स्ट और विज़न दोनों के लिए बेस्ट)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # सिस्टम इंस्ट्रक्शन और सर्च कॉन्टेक्स्ट तैयार करें
        base_instruction = (
            "You are Mehta AI, a highly accurate and updated assistant for 2026. "
            "You MUST always use the latest real-time internet data provided in the context. "
            "Never say 'no fresh data' or 'information not available' if any relevant information is present. "
            "Give direct, confident, and clear answers using the provided search results. "
            "Respond in the same language as the user.\n\n"
        )
        
        if search_context:
            base_instruction += f"[REAL-TIME INTERNET DATA - JUNE 2026]:\n{search_context}\n\n"
            
        content_parts = []
        
        # सिस्टम प्रॉम्प्ट को सबसे पहले जोड़ें
        content_parts.append(base_instruction)
        
        # 2. अगर यूज़र ने इमेज भेजी है, तो उसे बाइट्स में कन्वर्ट करके जोड़ें
        if image_data_url and "," in image_data_url:
            header, encoded = image_data_url.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            
            content_parts.append({
                "mime_type": mime_type,
                "data": image_bytes
            })
            
        # 3. यूज़र का टेक्स्ट मैसेज जोड़ें
        if user_message:
            content_parts.append(f"User Question: {user_message}")
        else:
            content_parts.append("Is image ko detail mein analyze karo.")
            
        # Gemini API से रिस्पॉन्स जेनरेट करें
        response = model.generate_content(content_parts)
        
        reply = response.text
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        
        return jsonify({"reply": clean_reply})
        
    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
