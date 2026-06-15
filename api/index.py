import os
import base64
import re
import requests
import datetime  
import random  # 🌟 Naya import: API keys rotate karne ke liye
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# API Keys Configuration
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Supabase Configuration (Automatically fetches variables from Vercel)
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

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
        
        user_id = data.get("user_id", "default_user")
        
        if not user_message and "messages" in data:
            messages = data.get("messages", [])
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if item.get("type") == "text":
                                user_message = item.get("text", "").strip()
                            elif item.get("type") == "image_url":
                                image_data_url = item.get("image_url", {}).get("url", None)
                    elif isinstance(content, str):
                        user_message = content.strip()

        if not user_message and not image_data_url:
            return jsonify({"error": "Message or image required"}), 400

        # ==============================================================
        # 🌟 NEW FEATURE 1: SMART DAILY LIMIT (40 Texts, Owner Unlimited)
        # ==============================================================
        ADMIN_EMAIL = "ratankumarmetha@gmail.com"  # Aapke liye koi limit nahi
        
        if user_id != ADMIN_EMAIL:
            try:
                # Aaj ki date nikalenge (UTC format me)
                today_start = datetime.datetime.utcnow().date().isoformat()
                
                # Supabase se check karega ki is user ne aaj kitne messages bheje
                user_chats = supabase.table("chat_history") \
                    .select("id") \
                    .eq("user_id", user_id) \
                    .gte("created_at", today_start) \
                    .execute()
                
                if len(user_chats.data) >= 40:
                    return jsonify({"reply": "⚠️ Aapki aaj ki free limit (40 messages) khatam ho gayi hai! Kripya kal dobara try karein."}), 429
            except Exception as limit_err:
                print(f"Limit Check Error: {limit_err}")

        # ==============================================================
        # 🌟 NEW FEATURE 2: API KEY ROTATION (Limit badhane ke liye)
        # ==============================================================
        api_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3")
        ]
        # Jo Keys Vercel me maujood hongi, sirf unme se random chusega
        valid_keys = [key for key in api_keys if key]
        if valid_keys:
            selected_key = random.choice(valid_keys)
            genai.configure(api_key=selected_key)
        # ==============================================================
            
        search_context = ""
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        # 🌟 तारीख डायनामिक कर दी गई है
        today_date = datetime.datetime.now().strftime("%d %B %Y")
        base_instruction = (
            f"You are Mehta AI, a highly accurate and updated assistant for 2026. Today is {today_date}. "
            "Your top priority is to look at the attached image carefully and identify the people or things inside it. "
            "Do NOT talk about Narendra Modi unless he is actually visible in the image. "
            "CRITICAL LANGUAGE RULE: Always respond in the exact same language used by the user. "
            "If the user interacts or asks a question in English, you must respond purely and fluently in English. "
            "If the user interacts in Hindi or Hinglish, respond naturally in Hindi/Hinglish. "
            "Ensure English-speaking users face absolutely no language barriers or forced translation."
        )
        
        model = genai.GenerativeModel(
            model_name="gemini-3.5-flash",
            system_instruction=base_instruction
        )
        
        content_parts = []
        if image_data_url:
            if "base64," in image_data_url:
                header, encoded = image_data_url.split("base64,", 1)
                mime_type = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
            else:
                encoded = image_data_url
                mime_type = "image/jpeg"
                
            try:
                image_bytes = base64.b64decode(encoded.strip())
                content_parts.append({
                    "mime_type": mime_type,
                    "data": image_bytes
                })
            except Exception as b64_err:
                print(f"Base64 Decode Error: {b64_err}")

        if search_context:
            content_parts.append(f"[REAL-TIME INTERNET DATA]:\n{search_context}\n\nUser Question: {user_message}")
        elif user_message:
            content_parts.append(user_message)
        else:
            content_parts.append("Look at this image carefully and tell me who or what is inside it.")
            
        response = model.generate_content(content_parts)
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', response.text).strip()
        
        print(f"BACKUP LOG - User: {user_id} | Client Msg: {user_message} | AI Reply: {clean_reply}")
        
        try:
            supabase.table("chat_history").insert({
                "user_id": user_id,
                "message": user_message if user_message else "[Image Sent]",
                "reply": clean_reply
            }).execute()
        except Exception as db_err:
            print(f"Database Save Error: {db_err}")
            
        return jsonify({"reply": clean_reply})
        
    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
