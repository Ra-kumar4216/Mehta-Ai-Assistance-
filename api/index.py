import os
import base64
import re
import requests
import datetime  
import random  
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# API Keys Configuration
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Supabase Configuration
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
        # 🌟 FEATURE 1: SMART DAILY LIMIT
        # ==============================================================
        ADMIN_EMAIL = "ratankumarmetha@gmail.com"  
        if user_id != ADMIN_EMAIL:
            try:
                today_start = datetime.datetime.utcnow().date().isoformat()
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
        # 🌟 FEATURE 2: API KEY ROTATION
        # ==============================================================
        api_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3")
        ]
        valid_keys = [key for key in api_keys if key]
        if valid_keys:
            selected_key = random.choice(valid_keys)
            genai.configure(api_key=selected_key)

        # ==============================================================
        # 🌟 FEATURE 3: MEMORY (Pichli baatein yaad rakhna)
        # ==============================================================
        past_history_context = ""
        try:
            history_response = supabase.table("chat_history") \
                .select("message, reply") \
                .eq("user_id", user_id) \
                .order("id", desc=True) \
                .limit(5) \
                .execute()
                
            if history_response.data:
                past_history_context = "[PAST CONVERSATION CONTEXT]\n"
                for row in reversed(history_response.data):
                    past_msg = row.get("message", "").replace("\n", " ")
                    past_reply = row.get("reply", "").replace("\n", " ")
                    if past_msg and past_reply and past_msg != "[Image Sent]":
                        past_history_context += f"User: {past_msg}\nMehta AI: {past_reply}\n\n"
        except Exception as hist_err:
            print(f"History fetch error: {hist_err}")
        # ==============================================================
            
        search_context = ""
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        today_date = datetime.datetime.now().strftime("%d %B %Y")
        
        # 🌟 MAIN FIX: 5 Bhashaon (Languages) ka strict rule lagaya gaya hai
        base_instruction = (
            f"You are Mehta AI, a highly accurate and updated assistant for 2026. Today is {today_date}. "
            "Your top priority is to look at the attached image carefully and identify the people or things inside it. "
            "Do NOT talk about Narendra Modi unless he is actually visible in the image. "
            "CRITICAL LANGUAGE RULE: You MUST respond in the EXACT same language as the [CURRENT QUESTION]. "
            "Do NOT get influenced by the language of the [PAST CONVERSATION CONTEXT]. "
            "You have strict expertise in 5 languages: English, Hindi, Hinglish, Tamil, and Telugu. "
            "- If the [CURRENT QUESTION] is in English, reply purely in English. "
            "- If the [CURRENT QUESTION] is in Hindi, reply purely in Hindi. "
            "- If the [CURRENT QUESTION] is in Hinglish, reply naturally in Hinglish. "
            "- If the [CURRENT QUESTION] is in Tamil (தமிழ்), reply fluently in Tamil. "
            "- If the [CURRENT QUESTION] is in Telugu (తెలుగు), reply fluently in Telugu. "
            "Always adapt to the user's preferred language instantly."
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

        final_prompt = past_history_context
        
        if search_context:
            final_prompt += f"[REAL-TIME INTERNET DATA]:\n{search_context}\n\n[CURRENT QUESTION]\nUser: {user_message}"
        elif user_message:
            final_prompt += f"[CURRENT QUESTION]\nUser: {user_message}"
        else:
            final_prompt += "[CURRENT QUESTION]\nLook at this image carefully and tell me who or what is inside it."
            
        content_parts.append(final_prompt)
        
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
