name: Instagram Bot Automations

on:
  schedule:
    - cron: '0 * * * *'  # Runs automatically every hour to check for new comments
  workflow_dispatch:
    inputs:
      post_url:
        description: 'Target Post URL (Leave blank to just run the bot)'
        required: false
        type: string
      keyword:
        description: 'Trigger Keyword (e.g. link)'
        required: false
        type: string
      reply_text:
        description: 'Public Reply Text'
        required: false
        type: string

jobs:
  run-bot:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Forces GitHub to fetch the full history, preventing conflicts

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install requests

      - name: Run Agent
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          # The inputs from the GitHub Web Form:
          INPUT_POST_URL: ${{ inputs.post_url }}
          INPUT_KEYWORD: ${{ inputs.keyword }}
          INPUT_REPLY: ${{ inputs.reply_text }}
        run: python agent.py

      - name: Save Rules and Progress
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          touch processed_comments.json rules.json
          git add processed_comments.json rules.json
          
          if ! git diff --staged --quiet; then
            git commit -m "chore: update bot rules and logs [skip ci]"
            
            # THE FIX: Download any new changes from GitHub before uploading
            git pull --rebase origin main
            
            git push
          else
            echo "No new rules or comments to save."
          fi
