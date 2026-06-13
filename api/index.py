import os
import base64
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)  # Frontend से कनेक्ट करने के लिए

# Vercel पर सेट की हुई GEMINI_API_KEY को कॉन्फ़िगर करें
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 🔥 आपका रियल-टाइम इंटरनेट सर्च फंक्शन
def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    try:
        with DDGS() as ddgs:
            results = []
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

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        image_data_url = data.get("image", None)  # Frontend से आने वाली Base64 इमेज
        
        if not user_message and not image_data_url:
            return jsonify({"error": "Message or image required"}), 400
            
        # 1. इंटरनेट सर्च चलाएं (अगर टेक्स्ट मैसेज है)
        search_context = ""
        if user_message:
            search_context = internet_search(user_message)
            
        # Gemini 2.5 Flash मॉडल लोड करें (यह फ़ास्ट है, विज़न और सर्च दोनों संभाल लेगा)
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
        
        # रिस्पॉन्स में से थिंकिंग टैग्स (यदि हों) को साफ़ करें
        reply = response.text
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', reply).strip()
        
        return jsonify({"reply": clean_reply})
        
    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
