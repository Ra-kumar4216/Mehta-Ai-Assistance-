import os
import base64
import re
import requests
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
        
        # Extract data if frontend sends payload in old OpenRouter format
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
            
        search_context = ""
        # Do not search internet if image is attached to avoid confusion
        if user_message and not image_data_url:
            search_context = internet_search(user_message)
            
        base_instruction = (
            "You are Mehta AI, a highly accurate and updated assistant for 2026. "
            "Your top priority is to look at the attached image carefully and identify the people or things inside it. "
            "Do NOT talk about Narendra Modi unless he is actually visible in the image. "
            "Respond directly, naturally, and clearly in Hindi/the user's language."
        )
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=base_instruction
        )
        
        content_parts = []
        
        # Clean Base64 data from Image URL and extract bytes
        if image_data_url:
            if "base64," in image_data_url:
                header, encoded = image_data_url.split("base64,", 1)
                mime_type = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
            else:
                encoded = image_data_url
                mime_type = "image/jpeg"
                
            try:
                # Remove extra spaces and decode
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
        
        # Save chat history securely to Supabase Database before returning response
        try:
            supabase.table("chat_history").insert({
                "user_id": "default_user",
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
