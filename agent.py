import os
import requests
import json
import re
from datetime import datetime

# --- Configuration & Secrets ---
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
IG_USER_ID = os.getenv('IG_USER_ID')

# --- Inputs from GitHub Web Form ---
INPUT_POST_URL = os.getenv('INPUT_POST_URL', '').strip()
INPUT_KEYWORD = os.getenv('INPUT_KEYWORD', '').lower().strip()
INPUT_REPLY = os.getenv('INPUT_REPLY', '').strip()

DB_FILE = "processed_comments.json"
RULES_FILE = "rules.json"
GRAPH_API_VERSION = "v19.0"

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} if filepath == RULES_FILE else []
    return {} if filepath == RULES_FILE else []

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

def extract_shortcode(url):
    match = re.search(r"(?:p|reel)/([^/?#&]+)", url)
    return match.group(1) if match else url

def main():
    if not ACCESS_TOKEN or not IG_USER_ID:
        print("❌ CONFIG ERROR: Missing Meta Secrets.")
        return

    # 1. Update Rules if the user filled out the GitHub form
    rules = load_json(RULES_FILE)
    if INPUT_POST_URL and INPUT_KEYWORD and INPUT_REPLY:
        shortcode = extract_shortcode(INPUT_POST_URL)
        if shortcode:
            # Save the new rule to our dictionary
            rules[shortcode] = {
                "keyword": INPUT_KEYWORD,
                "reply_text": INPUT_REPLY
            }
            save_json(RULES_FILE, rules)
            print(f"✅ NEW RULE SAVED: Post '{shortcode}' -> Keyword '{INPUT_KEYWORD}'")

    if not rules:
        print("⚠️ No rules configured yet. Go to GitHub Actions and add a rule!")
        return

    # 2. Run the Bot for all saved rules
    processed_list = load_json(DB_FILE)
    print(f"🤖 BOT STARTING: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch recent media to map shortcodes to actual Media IDs
    media_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_USER_ID}/media?fields=id,shortcode&limit=50&access_token={ACCESS_TOKEN}"
    media_items = requests.get(media_url).json().get('data', [])

    for media in media_items:
        shortcode = media.get('shortcode')
        
        # If this post has a rule setup in our database
        if shortcode in rules:
            rule = rules[shortcode]
            media_id = media['id']
            keyword = rule['keyword']
            reply_text = rule['reply_text']

            print(f"🔍 Checking Post '{shortcode}' for keyword '{keyword}'...")
            
            comments_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}/comments?access_token={ACCESS_TOKEN}"
            comments_resp = requests.get(comments_url).json()
            
            for comment in comments_resp.get('data', []):
                comment_id = comment.get('id')
                text = comment.get('text', '').lower()

                if keyword in text and comment_id not in processed_list:
                    print(f"  🎯 Match found! Comment ID: {comment_id}")

                    # Public Reply
                    reply_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{comment_id}/replies"
                    reply_resp = requests.post(reply_url, data={'message': reply_text, 'access_token': ACCESS_TOKEN}).json()
                    
                    if 'id' in reply_resp:
                        print("    ✅ Reply sent successfully.")
                    else:
                        print(f"    ⚠️ Failed to reply: {reply_resp}")

                    processed_list.append(comment_id)

    # Save the updated list of processed comments
    save_json(DB_FILE, processed_list)
    print("🏁 Bot finished checking all rules.")

if __name__ == "__main__":
    main()
