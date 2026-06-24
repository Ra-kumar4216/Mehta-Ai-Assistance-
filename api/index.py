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

# ✅ Models
TEXT_MODEL_PRIMARY = os.getenv("GROQ_TEXT_MODEL", "openai/gpt-oss-120b")
TEXT_MODEL_FALLBACK = os.getenv("GROQ_TEXT_MODEL_FALLBACK", "qwen/qwen3.6-27b")
VISION_MODEL_PRIMARY = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
VISION_MODEL_FALLBACK = os.getenv("GROQ_VISION_MODEL_FALLBACK", "qwen/qwen3.6-27b")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "ratankumarmetha@gmail.com")
DAILY_LIMIT = 50

def internet_search(query):
    if not query or len(query.strip()) < 2:
        return ""
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
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
            return "\n".join(unique_results)
    except Exception as e:
        print(f"Search Error: {e}")
    return ""

def call_groq(messages_payload, model_name, groq_api_key):
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": messages_payload, "temperature": 0.7, "max_tokens": 1024}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return response, None
    except Exception as e:
        return None, {"message": str(e)}

def check_and_increment_limit(user_id):
    if user_id == ADMIN_EMAIL: return True, None
    if not supabase: return True, None
    try:
        now = datetime.datetime.utcnow()
        row = supabase.table("chat_limits").select("*").eq("user_id", user_id).execute()
        if row.data:
            record = row.data[0]
            reset_at = datetime.datetime.fromisoformat(record["reset_at"]) if record.get("reset_at") else None
            if not reset_at or now >= reset_at:
                new_reset = (now + datetime.timedelta(hours=24)).isoformat()
                supabase.table("chat_limits").update({"count": 1, "reset_at": new_reset}).eq("user_id", user_id).execute()
                return True, None
            elif record.get("count", 0) >= DAILY_LIMIT:
                return False, record.get("reset_at")
            else:
                supabase.table("chat_limits").update({"count": record.get("count", 0) + 1}).eq("user_id", user_id).execute()
                return True, None
        else:
            new_reset = (now + datetime.timedelta(hours=24)).isoformat()
            supabase.table("chat_limits").insert({"user_id": user_id, "count": 1, "reset_at": new_reset}).execute()
            return True, None
    except Exception as limit_err:
        print(f"Limit check error: {limit_err}")
        return True, None

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        image_data_url = data.get("image", None)
        user_id = data.get("user_id", "default_user")

        if not user_message and "messages" in data:
            for msg in data["messages"]:
                if msg.get("role") == "user":
                    content = msg.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if item.get("type") == "text": user_message = item.get("text", "").strip()
                            elif item.get("type") == "image_url": image_data_url = item.get("image_url", {}).get("url", None)
                    elif isinstance(content, str): user_message = content.strip()

        if not user_message and not image_data_url:
            return jsonify({"error": "Message or image required"}), 400

        allowed, reset_at = check_and_increment_limit(user_id)
        if not allowed:
            return jsonify({"reply": "⚠️ Daily limit khatam ho gaya.", "reset_at": reset_at}), 429

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key: return jsonify({"reply": "API Key missing"}), 500

        today_date = datetime.datetime.now().strftime("%d %B %Y")
        system_instruction = (
            f"You are Mehta AI. Today is {today_date}. You were founded by Ratan Kumar. "
            "If asked about founder, say Ratan Kumar. Respond in the user's language."
        )
        
        messages_payload = [{"role": "system", "content": system_instruction}]

        if not image_data_url and supabase:
            try:
                hist = supabase.table("chat_history").select("message, reply").eq("user_id", user_id).order("id", desc=True).limit(4).execute()
                for row in reversed(hist.data):
                    messages_payload.append({"role": "user", "content": row["message"]})
                    messages_payload.append({"role": "assistant", "content": row["reply"]})
            except: pass

        final_prompt = f"[CURRENT QUESTION]\nUser: {user_message or 'Describe this image.'}"
        
        if image_data_url:
            if not image_data_url.startswith("data:image"): image_data_url = f"data:image/jpeg;base64,{image_data_url}"
            messages_payload.append({"role": "user", "content": [{"type": "text", "text": final_prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]})
            primary_model, fallback_model = VISION_MODEL_PRIMARY, VISION_MODEL_FALLBACK
        else:
            messages_payload.append({"role": "user", "content": final_prompt})
            primary_model, fallback_model = TEXT_MODEL_PRIMARY, TEXT_MODEL_FALLBACK

        response, conn_err = call_groq(messages_payload, primary_model, groq_api_key)
        if conn_err or response.status_code != 200:
            response, _ = call_groq(messages_payload, fallback_model, groq_api_key)

        reply = response.json()['choices'][0]['message']['content'].strip()
        
        if supabase:
            supabase.table("chat_history").insert({"user_id": user_id, "message": user_message or "[Image]", "reply": reply}).execute()
            
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Server Error: {str(e)}"}), 500
