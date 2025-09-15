# Telegram Image Gallery

A web-based image gallery that uses a Telegram group as a backend for storing and retrieving images. Built with FastAPI and featuring a responsive frontend with full control over animations and features.

## Features

- Uses Telegram group as image storage backend
- Responsive web gallery with mobile support
- Lightbox functionality for viewing images
- Lazy loading for improved performance
- Smooth animations and transitions
- Full control over UI/UX features

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS (Tailwind), JavaScript (Alpine.js)
- **Hosting**: Render (free tier)
- **Storage**: Telegram servers (via Bot API)

## Project Structure

```
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   └── index.html       # Main gallery page
├── static/              # Static assets
│   ├── css/             # Stylesheets
│   │   └── style.css    # Custom styles
│   └── js/              # JavaScript files
│       └── main.js      # Gallery functionality
```

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Access the gallery**:
   Open your browser to `http://localhost:8000`

## Telegram Bot Setup

Follow the detailed instructions in [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) to:

1. Create a Telegram bot using BotFather
2. Configure bot privacy settings
3. Add the bot to your Telegram group
4. Set up the webhook for receiving updates

## Deployment to Render

1. Create a new web service on Render
2. Connect your Git repository
3. Set the build command to: `pip install -r requirements.txt`
4. Set the start command to: `python main.py`
5. Add environment variables in the Render dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

## Development

To add test data for development:
```
GET /api/test-data
```

To manually set up the webhook (when deployed):
```
GET /setup-webhook
```

## API Endpoints

- `GET /` - Main gallery page
- `GET /api/images` - Get all images metadata
- `POST /api/telegram/webhook` - Telegram webhook endpoint
- `GET /api/test-data` - Add test images (development only)
- `GET /setup-webhook` - Set up Telegram webhook (when deployed)
- `GET /health` - Health check endpoint

## Customization

You can customize the gallery by modifying:

- `templates/index.html` - HTML structure and layout
- `static/css/style.css` - Custom styles and animations
- `static/js/main.js` - JavaScript functionality
- `main.py` - Backend logic and API endpoints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is licensed under the MIT License.