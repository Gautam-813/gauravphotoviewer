from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import asyncio
import logging
from typing import List, Dict
import os
import aiohttp
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Telegram Image Gallery")

# Get port from environment variable (Render sets this)
PORT = int(os.environ.get("PORT", 8000))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# In-memory storage for image data (in production, use a database)
# This will store image metadata fetched from Telegram
images_data: List[Dict] = []

# Telegram bot configuration (to be set via environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    """Serve the main gallery page"""
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile = any(device in user_agent for device in ["mobile", "android", "iphone", "ipad"])
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Telegram Image Gallery",
        "is_mobile": is_mobile
    })

@app.get("/api/images")
async def get_images():
    """API endpoint to get images data"""
    # Return the stored image data
    # In a real implementation, this would fetch from database
    return {"images": images_data}

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram updates"""
    update_data = await request.json()
    logger.info(f"Received Telegram update: {update_data}")
    
    # Process the update
    await process_telegram_update(update_data)
    
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Telegram Image Gallery is running!"}

@app.get("/test")
async def test_page(request: Request):
    """Test page to verify the server is working"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Telegram Image Gallery - Test"
    })

async def process_telegram_update(update_data: dict):
    """Process incoming Telegram updates and extract image data"""
    try:
        # Check if this is a message update
        if "message" in update_data:
            message = update_data["message"]
            
            # Check if message contains photo
            if "photo" in message:
                await process_photo_message(message)
            # Check if message contains document (images sent as files)
            elif "document" in message and is_image_document(message["document"]):
                await process_document_message(message)
                
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")

async def process_photo_message(message: dict):
    """Process a message containing a photo"""
    # Get the largest photo (last in the sizes array)
    photos = message["photo"]
    largest_photo = photos[-1]  # Last photo is the largest
    
    # Get file path from Telegram API
    file_path = await get_file_path(largest_photo["file_id"])
    
    if file_path:
        # Extract image data
        image_data = {
            "id": largest_photo["file_id"],
            "file_id": largest_photo["file_id"],
            "file_unique_id": largest_photo["file_unique_id"],
            "width": largest_photo["width"],
            "height": largest_photo["height"],
            "timestamp": message.get("date", datetime.now().isoformat()),
            "caption": message.get("caption", ""),
            "message_id": message["message_id"],
            "thumb_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
            "full_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        }
        
        # Add to our images data (in production, save to database)
        images_data.append(image_data)
        logger.info(f"Added new image: {image_data['file_id']}")

async def process_document_message(message: dict):
    """Process a message containing an image document"""
    document = message["document"]
    
    # Get file path from Telegram API
    file_path = await get_file_path(document["file_id"])
    
    if file_path:
        # Extract image data
        image_data = {
            "id": document["file_id"],
            "file_id": document["file_id"],
            "file_unique_id": document["file_unique_id"],
            "file_name": document["file_name"],
            "mime_type": document["mime_type"],
            "timestamp": message.get("date", datetime.now().isoformat()),
            "caption": message.get("caption", ""),
            "message_id": message["message_id"],
            "thumb_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
            "full_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        }
        
        # Add to our images data (in production, save to database)
        images_data.append(image_data)
        logger.info(f"Added new document image: {image_data['file_id']}")

def is_image_document(document: dict) -> bool:
    """Check if a document is an image based on MIME type"""
    mime_type = document.get("mime_type", "")
    return mime_type.startswith("image/")

async def get_file_path(file_id: str) -> str:
    """Get the file path from Telegram API"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return ""
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return data["result"]["file_path"]
                    else:
                        logger.error(f"Telegram API error: {data}")
                else:
                    logger.error(f"HTTP error {response.status} when getting file path")
    except Exception as e:
        logger.error(f"Error getting file path: {e}")
    
    return ""

# For development/testing purposes
@app.get("/api/test-data")
async def add_test_data():
    """Add some test data for development"""
    test_images = [
        {
            "id": "test1",
            "file_id": "test1",
            "file_unique_id": "unique1",
            "width": 800,
            "height": 600,
            "timestamp": datetime.now().isoformat(),
            "caption": "Beautiful landscape",
            "message_id": 1,
            "thumb_url": "https://picsum.photos/300/300?random=1",
            "full_url": "https://picsum.photos/800/600?random=1"
        },
        {
            "id": "test2",
            "file_id": "test2",
            "file_unique_id": "unique2",
            "width": 800,
            "height": 600,
            "timestamp": datetime.now().isoformat(),
            "caption": "City skyline at night",
            "message_id": 2,
            "thumb_url": "https://picsum.photos/300/300?random=2",
            "full_url": "https://picsum.photos/800/600?random=2"
        }
    ]
    
    global images_data
    images_data.extend(test_images)
    return {"status": "Test data added", "count": len(test_images)}

# Endpoint to manually trigger webhook setup (for testing)
@app.get("/setup-webhook")
async def setup_webhook(request: Request):
    """Setup webhook for Telegram bot"""
    try:
        # Get the base URL of this application
        base_url = str(request.base_url).rstrip("/")
        webhook_url = f"{base_url}/api/telegram/webhook"
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return {"status": "success", "message": f"Webhook set to {webhook_url}"}
                    else:
                        return {"status": "error", "message": f"Telegram API error: {data}"}
                else:
                    return {"status": "error", "message": f"HTTP error {response.status}"}
    except Exception as e:
        return {"status": "error", "message": f"Exception: {e}"}

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(app, host="0.0.0.0", port=port)