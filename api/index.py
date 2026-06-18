import os
import base64
import re
import requests
import datetime  
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai              
from google.genai import types        
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Supabase Configuration
supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
    except Exception as e:
        print("Supabase Init Error:", e)
        supabase = None
else:
    supabase = None

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

        ADMIN_EMAIL = "ratankumarmetha@gmail.com"
        DAILY_CHAT_LIMIT = 50

        if supabase and user_id != ADMIN_EMAIL:
            try:
                today_start = datetime.datetime.utcnow().date().isoformat()
                user_chats = supabase.table("chat_history") \
                    .select("id, created_at") \
                    .eq("user_id", user_id) \
                    .gte("created_at", today_start) \
                    .order("created_at", desc=False) \
                    .execute()

                if len(user_chats.data) >= DAILY_CHAT_LIMIT:
                    tomorrow_utc = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
                    reset_at = datetime.datetime.combine(
                        tomorrow_utc, datetime.time.min, tzinfo=datetime.timezone.utc
                    ).isoformat()

                    return jsonify({
                        "reply": "⚠️ Aapki aaj ki free limit (50 chats) khatam ho gayi hai! Kripya 24 ghante baad dobara try karein.",
                        "error": "daily_limit_reached",
                        "reset_at": reset_at,
                        "limit": DAILY_CHAT_LIMIT
                    }), 429
            except Exception as limit_err:
                print(f"Limit Check Error: {limit_err}")

        past_history_context = ""
        if supabase:
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
            
        search_context = ""
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        today_date = datetime.datetime.now().strftime("%d %B %Y")
        
        base_instruction = (
            f"You are Mehta AI, a highly accurate and updated assistant for 2026. Today is {today_date}. "
            "Your top priority is to look at the attached image carefully and identify the people or things inside it. "
            "Do NOT talk about Narendra Modi unless he is actually visible in the image. "
            "CRITICAL LANGUAGE RULE: You MUST respond in the EXACT same language as the [CURRENT QUESTION]. "
            "Do NOT get influenced by the language of the [PAST CONVERSATION CONTEXT]. "
            "You have strict expertise in 5 languages: English, Hindi, Hinglish, Tamil, and Telugu. "
            "Always adapt to the user's preferred language instantly."
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
                content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
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

        # ==============================================================
        # 🌟 FEATURE: SEQUENTIAL API KEY FALLBACK (1 -> 2 -> 3 -> 4)
        # ==============================================================
        api_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4") # ✅ Chauthi key bhi add kar di
        ]
        
        # Jo keys khali (None) nahi hain, unhe ek list mein daal lo
        valid_keys = [key for key in api_keys if key]
        
        if not valid_keys:
            return jsonify({"reply": "Server Configuration Error: Koi API key nahi mili."}), 500

        ai_response = None
        last_error = ""

        # Loop har key ko ek-ek karke try karega
        for key in valid_keys:
            try:
                client = genai.Client(api_key=key)
                ai_response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=content_parts,
                    config=types.GenerateContentConfig(
                        system_instruction=base_instruction
                    )
                )
                # Agar reply mil gaya toh loop se bahar aa jao (Agli key test nahi hogi)
                break
            except Exception as e:
                # Agar error aaya (jaise limit over), toh agle loop me agli key try hogi
                print(f"Key fail hui, agli try kar rahe hain... Error: {e}")
                last_error = str(e)
                continue

        # Agar chaaro ki chaaro keys fail ho jayein:
        if not ai_response:
            return jsonify({"reply": "⚠️ Server Error: Sabhi API keys ki daily limit khatam ho chuki hai."}), 500
        
        # ==============================================================

        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', ai_response.text).strip()
        
        if supabase:
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
        print(f"Chat Error: {str(e)}")
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
