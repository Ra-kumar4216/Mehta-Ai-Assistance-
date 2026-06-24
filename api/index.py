import os
import base64
import re
import requests
import datetime  
from flask import Flask, request, jsonify
from flask_cors import CORS
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

# ✅ Models ab env se aate hain, hardcode nahi.
# Groq jab bhi koi model deprecate kare, sirf Vercel env variable update karo, code touch nahi karna.
TEXT_MODEL_PRIMARY = os.getenv("GROQ_TEXT_MODEL", "openai/gpt-oss-120b")
TEXT_MODEL_FALLBACK = os.getenv("GROQ_TEXT_MODEL_FALLBACK", "qwen/qwen3.6-27b")

VISION_MODEL_PRIMARY = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
VISION_MODEL_FALLBACK = os.getenv("GROQ_VISION_MODEL_FALLBACK", "qwen/qwen3.6-27b")

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

def call_groq(messages_payload, model_name, groq_api_key):
    """Single Groq API call. Returns (response_obj_or_None, error_dict_or_None)."""
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": messages_payload,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=30
        )
        return response, None
    except Exception as e:
        return None, {"message": str(e)}

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
                        "reply": "⚠️ Your limit is expire re try after 24 hr.",
                        "error": "daily_limit_reached",
                        "reset_at": reset_at,
                        "limit": DAILY_CHAT_LIMIT
                    }), 429
            except Exception as limit_err:
                print(f"Limit Check Error: {limit_err}")

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return jsonify({"reply": "Server Configuration Error: GROQ_API_KEY nahi mili."}), 500

        messages_payload = []
        today_date = datetime.datetime.now().strftime("%d %B %Y")
        system_instruction = (
            f"You are Mehta AI, a highly accurate and updated assistant for 2026. Today is {today_date}. "
            "Your top priority is to look at the attached image carefully and identify the people or things inside it. "
            "Do NOT talk about Narendra Modi unless he is actually visible in the image. "
            "CRITICAL LANGUAGE RULE: You MUST respond in the EXACT same language as the [CURRENT QUESTION]. "
            "Do NOT get influenced by the language of the [PAST CONVERSATION CONTEXT]. "
            "You have strict expertise in 5 languages: English, Hindi, Hinglish, Tamil, and Telugu. "
            "Always adapt to the user's preferred language instantly. "
            "ANSWER STYLE: Give clear, direct, to-the-point answers. Do NOT pad responses with "
            "excessive detail, repetition, or unnecessary disclaimers. Be accurate, but prioritize "
            "clarity and brevity over exhaustive explanation unless the user explicitly asks for depth."
        )
        messages_payload.append({"role": "system", "content": system_instruction})

        # ✅ FIXED: Groq Vision models history support nahi karte. 
        # Isliye ab history sirf tab jayegi jab image NAHI hogi.
        if not image_data_url and supabase:
            try:
                history_response = supabase.table("chat_history") \
                    .select("message, reply") \
                    .eq("user_id", user_id) \
                    .order("id", desc=True) \
                    .limit(4) \
                    .execute()
                    
                if history_response.data:
                    for row in reversed(history_response.data):
                        past_msg = row.get("message", "").replace("\n", " ")
                        past_reply = row.get("reply", "").replace("\n", " ")
                        if past_msg and past_reply and past_msg != "[Image Sent]":
                            messages_payload.append({"role": "user", "content": past_msg})
                            messages_payload.append({"role": "assistant", "content": past_reply})
            except Exception as hist_err:
                print(f"History fetch error: {hist_err}")
            
        search_context = ""
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        final_text_prompt = ""
        if search_context:
            final_text_prompt += f"[REAL-TIME INTERNET DATA]:\n{search_context}\n\n"
        final_text_prompt += f"[CURRENT QUESTION]\nUser: {user_message if user_message else 'Look at this image carefully and tell me what is inside it.'}"

        if image_data_url:
            if not image_data_url.startswith("data:image"):
                image_data_url = f"data:image/jpeg;base64,{image_data_url}"
            current_content = [
                {"type": "text", "text": final_text_prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]
            messages_payload.append({"role": "user", "content": current_content})
            primary_model = VISION_MODEL_PRIMARY
            fallback_model = VISION_MODEL_FALLBACK
        else:
            messages_payload.append({"role": "user", "content": final_text_prompt})
            primary_model = TEXT_MODEL_PRIMARY
            fallback_model = TEXT_MODEL_FALLBACK

        # ✅ Try primary model first, agar decommissioned/rate-limited mile to fallback try karo.
        response, conn_err = call_groq(messages_payload, primary_model, groq_api_key)
        used_model = primary_model

        needs_fallback = conn_err is not None or (response is not None and response.status_code in (400, 404, 429, 500, 503))

        if needs_fallback and fallback_model and fallback_model != primary_model:
            print(f"Primary model '{primary_model}' failed, trying fallback '{fallback_model}'")
            response, conn_err = call_groq(messages_payload, fallback_model, groq_api_key)
            used_model = fallback_model

        if conn_err is not None:
            print(f"Groq Connection Error: {conn_err}")
            return jsonify({"reply": "⚠️ AI service abhi response nahi de raha. Thodi der me try karo."}), 500

        if response.status_code != 200:
            print(f"Groq Error ({used_model}): {response.text}")
            return jsonify({"reply": f"⚠️ API Error: Server issue. ({response.status_code})"}), 500

        response_data = response.json()
        clean_reply = response_data['choices'][0]['message']['content'].strip()
        clean_reply = re.sub(r'<think>[\s\S]*?</think>', '', clean_reply).strip()

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
