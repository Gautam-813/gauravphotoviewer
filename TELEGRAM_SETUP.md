# Telegram Bot Setup Guide

## Step 1: Create a Telegram Bot

1. Open Telegram and search for @BotFather
2. Start a chat with BotFather
3. Send the command `/newbot` to create a new bot
4. Follow the prompts to:
   - Give your bot a name (e.g., "My Gallery Bot")
   - Choose a username for your bot (must end in "bot", e.g., "my_gallery_bot")
5. BotFather will provide you with a **Token** - save this securely

## Step 2: Configure Bot Settings

1. Send `/setprivacy` to BotFather
2. Select your bot
3. Choose "Disable" - this allows the bot to see all messages in groups
4. Send `/setjoingroups` to BotFather
5. Select your bot
6. Choose "Enable" - this allows the bot to be added to groups

## Step 3: Get Your Chat ID

1. Add your bot to your Telegram group
2. Make the bot an administrator in the group:
   - Go to group settings
   - Tap "Administrators"
   - Add your bot and give it admin rights
3. Send a test message in the group
4. To get the chat ID, you can:
   - Visit: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   - Look for the "chat" object in the response
   - The "id" field is your chat ID

## Step 4: Configure Environment Variables

Create a `.env` file in your project root with:

```
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHAT_ID=your_actual_chat_id_here
```

## Step 5: Set Up Webhook

Once your application is deployed, you need to set up the webhook:

1. Visit: `https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://your-app-url.com/api/telegram/webhook`
2. Replace `your-app-url.com` with your actual deployed URL
3. You should get a response: `{"ok":true,"result":true,"description":"Webhook was set"}`

## Step 6: Test the Integration

1. Send an image to your Telegram group
2. Visit your gallery website
3. The image should appear in the gallery after a few seconds

## Troubleshooting

- If images don't appear, check the server logs
- Ensure the bot has admin rights in the group
- Verify the privacy mode is disabled
- Check that the webhook URL is correct and accessible