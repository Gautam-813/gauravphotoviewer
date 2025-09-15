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

# Set up logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Telegram Image Gallery application")

# Get port from environment variable (Render sets this)
PORT = int(os.environ.get("PORT", 8000))
logger.info(f"Configured port: {PORT}")

# Initialize FastAPI app
app = FastAPI(title="Telegram Image Gallery")
logger.info("FastAPI app initialized")

# Mount static files directory
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted")
except Exception as e:
    logger.error(f"Error mounting static files: {e}")

# Set up Jinja2 templates
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Templates initialized")
except Exception as e:
    logger.error(f"Error initializing templates: {e}")

# Persistent storage for image data
import json
from pathlib import Path

# Storage file path
STORAGE_FILE = "images_storage.json"

# Load existing images from file or create empty list
def load_images_from_storage():
    """Load images from persistent storage file"""
    try:
        if Path(STORAGE_FILE).exists():
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} images from storage")
                return data
        else:
            logger.info("No existing storage file found, starting with empty gallery")
            return []
    except Exception as e:
        logger.error(f"Error loading images from storage: {e}")
        return []

def save_images_to_storage():
    """Save images to persistent storage file"""
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(images_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(images_data)} images to storage")
    except Exception as e:
        logger.error(f"Error saving images to storage: {e}")

# Load images from persistent storage
images_data: List[Dict] = load_images_from_storage()
logger.info(f"Image data storage initialized with {len(images_data)} existing photos")

# Telegram bot configuration (to be set via environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
logger.info("Environment variables loaded")

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete")
    logger.info(f"Application is ready to accept connections on port {PORT}")
    
    # Auto-fetch history if storage is empty (first time setup)
    if len(images_data) == 0:
        logger.info("Empty storage detected, fetching chat history...")
        try:
            historical_photos = await fetch_chat_history()
            if historical_photos:
                global images_data
                images_data.extend(historical_photos)
                save_images_to_storage()
                logger.info(f"Auto-loaded {len(historical_photos)} photos from chat history")
            else:
                logger.info("No historical photos found in chat")
        except Exception as e:
            logger.error(f"Error auto-fetching history: {e}")
    else:
        logger.info(f"Found {len(images_data)} existing photos in storage")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    """Serve the main gallery page"""
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile = any(device in user_agent for device in ["mobile", "android", "iphone", "ipad"])
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Gaurav's Photos - Precious Moments",
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
    return {"status": "healthy", "message": "Gaurav's Photo Gallery is running!", "port": PORT}

@app.get("/sw.js")
async def service_worker():
    """Serve the service worker"""
    from fastapi.responses import FileResponse
    return FileResponse("static/sw.js", media_type="application/javascript")

@app.get("/manifest.json")
async def manifest():
    """Serve the PWA manifest"""
    from fastapi.responses import FileResponse
    return FileResponse("static/manifest.json", media_type="application/json")

@app.get("/api/storage-info")
async def storage_info():
    """Get storage information"""
    storage_exists = Path(STORAGE_FILE).exists()
    storage_size = Path(STORAGE_FILE).stat().st_size if storage_exists else 0
    return {
        "storage_file": STORAGE_FILE,
        "exists": storage_exists,
        "size_bytes": storage_size,
        "total_images": len(images_data),
        "status": "Storage is working properly! 📸✨"
    }

@app.get("/api/fetch-history")
async def fetch_history():
    """Manually fetch all photos from Telegram chat history"""
    try:
        logger.info("Manual history fetch requested")
        historical_photos = await fetch_chat_history()
        
        if historical_photos:
            # Add historical photos to our storage
            global images_data
            initial_count = len(images_data)
            
            # Add new photos (duplicates are already filtered out)
            for photo in historical_photos:
                images_data.append(photo)
            
            # Save to persistent storage
            save_images_to_storage()
            
            new_count = len(images_data) - initial_count
            logger.info(f"Added {new_count} historical photos")
            
            return {
                "status": "success",
                "message": f"Fetched {len(historical_photos)} photos from history",
                "new_photos_added": new_count,
                "total_photos": len(images_data)
            }
        else:
            return {
                "status": "success", 
                "message": "No new historical photos found",
                "new_photos_added": 0,
                "total_photos": len(images_data)
            }
            
    except Exception as e:
        logger.error(f"Error in manual history fetch: {e}")
        return {
            "status": "error",
            "message": f"Failed to fetch history: {str(e)}"
        }

@app.get("/test")
async def test_page(request: Request):
    """Test page to verify the server is working"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Gaurav's Photos - Test Page"
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
        
        # Add to our images data and save to persistent storage
        images_data.append(image_data)
        save_images_to_storage()  # Save to file immediately
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
        
        # Add to our images data and save to persistent storage
        images_data.append(image_data)
        save_images_to_storage()  # Save to file immediately
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

async def fetch_chat_history():
    """Fetch all existing photos from Telegram group chat history"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return []
    
    logger.info("Fetching chat history to get existing photos...")
    all_photos = []
    offset = 0
    limit = 100  # Telegram API limit per request
    
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                # Get chat history using getUpdates with offset
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
                params = {
                    "offset": offset,
                    "limit": limit,
                    "timeout": 10
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"HTTP error {response.status} when fetching chat history")
                        break
                    
                    data = await response.json()
                    if not data.get("ok"):
                        logger.error(f"Telegram API error: {data}")
                        break
                    
                    updates = data.get("result", [])
                    if not updates:
                        break  # No more updates
                    
                    # Process each update for photos
                    for update in updates:
                        if "message" in update:
                            message = update["message"]
                            
                            # Check if message is from our target chat
                            if str(message.get("chat", {}).get("id")) == str(TELEGRAM_CHAT_ID):
                                # Process photos in this message
                                if "photo" in message:
                                    photo_data = await process_photo_message_history(message)
                                    if photo_data:
                                        all_photos.append(photo_data)
                                elif "document" in message and is_image_document(message["document"]):
                                    photo_data = await process_document_message_history(message)
                                    if photo_data:
                                        all_photos.append(photo_data)
                    
                    # Update offset for next batch
                    if updates:
                        offset = updates[-1]["update_id"] + 1
                    else:
                        break
                    
                    # Limit to prevent infinite loop (adjust as needed)
                    if len(all_photos) > 1000:  # Safety limit
                        logger.warning("Reached safety limit of 1000 photos from history")
                        break
        
        logger.info(f"Fetched {len(all_photos)} photos from chat history")
        return all_photos
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return []

async def process_photo_message_history(message: dict):
    """Process a photo message from chat history"""
    try:
        photos = message["photo"]
        largest_photo = photos[-1]  # Last photo is the largest
        
        # Check if we already have this photo (avoid duplicates)
        existing_photo = next((img for img in images_data if img["file_id"] == largest_photo["file_id"]), None)
        if existing_photo:
            return None  # Skip duplicate
        
        file_path = await get_file_path(largest_photo["file_id"])
        if file_path:
            return {
                "id": largest_photo["file_id"],
                "file_id": largest_photo["file_id"],
                "file_unique_id": largest_photo["file_unique_id"],
                "width": largest_photo["width"],
                "height": largest_photo["height"],
                "timestamp": message.get("date", datetime.now().timestamp()),
                "caption": message.get("caption", ""),
                "message_id": message["message_id"],
                "thumb_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                "full_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                "from_history": True  # Mark as historical photo
            }
    except Exception as e:
        logger.error(f"Error processing photo from history: {e}")
    return None

async def process_document_message_history(message: dict):
    """Process a document message from chat history"""
    try:
        document = message["document"]
        
        # Check if we already have this document (avoid duplicates)
        existing_doc = next((img for img in images_data if img["file_id"] == document["file_id"]), None)
        if existing_doc:
            return None  # Skip duplicate
        
        file_path = await get_file_path(document["file_id"])
        if file_path:
            return {
                "id": document["file_id"],
                "file_id": document["file_id"],
                "file_unique_id": document["file_unique_id"],
                "file_name": document["file_name"],
                "mime_type": document["mime_type"],
                "timestamp": message.get("date", datetime.now().timestamp()),
                "caption": message.get("caption", ""),
                "message_id": message["message_id"],
                "thumb_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                "full_url": f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                "from_history": True  # Mark as historical photo
            }
    except Exception as e:
        logger.error(f"Error processing document from history: {e}")
    return None

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
    save_images_to_storage()  # Save test data to storage too
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
    logger.info(f"Starting server on port {port}")
    
    # Log startup information
    logger.info("Starting uvicorn server...")
    logger.info(f"Host: 0.0.0.0, Port: {port}")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise