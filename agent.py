import os
import json
import re
import requests

# --------------------------
# Configuration & Env Vars
# --------------------------
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")

# Optional inputs from GitHub Actions manual trigger
INPUT_POST_URL = os.environ.get("INPUT_POST_URL", "").strip()
INPUT_KEYWORD = os.environ.get("INPUT_KEYWORD", "").strip()
INPUT_REPLY = os.environ.get("INPUT_REPLY", "").strip()

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

RULES_FILE = "rules.json"
PROCESSED_FILE = "processed_comments.json"

# --------------------------
# Helper Functions
# --------------------------
def load_json(filepath, default_data):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_data
    return default_data

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def extract_shortcode(url):
    """Extracts the Instagram shortcode from /p/ or /reel/ URLs."""
    match = re.search(r'/(?:p|reel)/([^/?#&]+)', url)
    return match.group(1) if match else None

# --------------------------
# Main Bot Logic
# --------------------------
def main():
    if not ACCESS_TOKEN or not IG_USER_ID:
        print("❌ ERROR: ACCESS_TOKEN or IG_USER_ID environment variables are missing!")
        return

    print("🚀 Starting Instagram Auto-Reply Bot...")

    # 1. Load Databases
    rules = load_json(RULES_FILE, {})
    processed_comments = load_json(PROCESSED_FILE, [])

    # 2. Add New Rule if inputs are provided
    if INPUT_POST_URL and INPUT_KEYWORD and INPUT_REPLY:
        shortcode = extract_shortcode(INPUT_POST_URL)
        if shortcode:
            rules[shortcode] = {
                "keyword": INPUT_KEYWORD.lower(),
                "reply": INPUT_REPLY
            }
            save_json(RULES_FILE, rules)
            print(f"📝 Added new rule for shortcode '{shortcode}': Trigger '{INPUT_KEYWORD}' -> Reply '{INPUT_REPLY}'")
        else:
            print("⚠️ Could not extract shortcode from provided URL. Skipping rule addition.")

    if not rules:
        print("🤷 No rules configured. Exiting.")
        return

    # 3. Fetch Recent Media Items
    print("📡 Fetching recent media items...")
    media_url = f"{BASE_URL}/{IG_USER_ID}/media"
    media_params = {
        "fields": "shortcode,id",
        "limit": 50,
        "access_token": ACCESS_TOKEN
    }
    
    media_response = requests.get(media_url, params=media_params).json()
    if "error" in media_response:
        print(f"❌ API Error fetching media: {media_response['error']}")
        return

    media_items = media_response.get("data", [])
    print(f"✅ Fetched {len(media_items)} media items.")

    # 4. Process Comments for Matching Media
    changes_made = False

    for item in media_items:
        shortcode = item.get("shortcode")
        media_id = item.get("id")

        if shortcode in rules:
            rule = rules[shortcode]
            keyword = rule["keyword"]
            reply_text = rule["reply"]

            print(f"🔍 Checking comments for media ID {media_id} (Shortcode: {shortcode})...")
            
            comments_url = f"{BASE_URL}/{media_id}/comments"
            comments_params = {
                "fields": "id,text",
                "access_token": ACCESS_TOKEN
            }
            
            comments_response = requests.get(comments_url, params=comments_params).json()
            comments = comments_response.get("data", [])

            for comment in comments:
                c_id = comment.get("id")
                c_text = comment.get("text", "")

                # Check if unreplied and contains keyword
                if c_id not in processed_comments and keyword in c_text.lower():
                    print(f"🎯 Match found! Comment ({c_id}): '{c_text}'")
                    
                    # 5. Post Reply
                    reply_url = f"{BASE_URL}/{c_id}/replies"
                    reply_data = {
                        "message": reply_text,
                        "access_token": ACCESS_TOKEN
                    }
                    
                    reply_res = requests.post(reply_url, data=reply_data).json()
                    
                    if "id" in reply_res:
                        print(f"✅ Successfully replied to {c_id}")
                        processed_comments.append(c_id)
                        changes_made = True
                    else:
                        print(f"❌ Failed to reply to {c_id}. API Response: {reply_res}")

    # 6. Save State
    if changes_made:
        save_json(PROCESSED_FILE, processed_comments)
        print("💾 State updated and saved to processed_comments.json.")
    else:
        print("💤 No new matching comments found. Nothing to update.")

    print("🏁 Bot finished successfully.")

if __name__ == "__main__":
    main()
