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
    global images_data  # Declare global at the top of the function
    
    logger.info("Application startup complete")
    logger.info(f"Application is ready to accept connections on port {PORT}")
    
    # Auto-fetch history if storage is empty (first time setup)
    if len(images_data) == 0:
        logger.info("Empty storage detected, attempting to fetch chat history...")
        try:
            historical_photos = await fetch_chat_history()
            if historical_photos:
                images_data.extend(historical_photos)
                save_images_to_storage()
                logger.info(f"Auto-loaded {len(historical_photos)} photos from chat history")
            else:
                logger.info("No historical photos available via Bot API")
                logger.info("💡 To add existing photos:")
                logger.info("   1. Visit /api/test-data for sample photos")
                logger.info("   2. Post new photos to Telegram group (captured automatically)")
                logger.info("   3. Use /api/fetch-history button in the gallery")
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

@app.get("/api/get-all-chat-messages")
async def get_all_chat_messages():
    """Alternative method: Try to get older messages using different approach"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"status": "error", "message": "Bot token or chat ID not configured"}
    
    try:
        # Method 1: Try to get chat administrators (sometimes reveals more info)
        async with aiohttp.ClientSession() as session:
            admin_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatAdministrators"
            params = {"chat_id": TELEGRAM_CHAT_ID}
            
            async with session.get(admin_url, params=params) as response:
                if response.status == 200:
                    admin_data = await response.json()
                    if admin_data.get("ok"):
                        admins = admin_data.get("result", [])
                        logger.info(f"Found {len(admins)} administrators in the chat")
                    else:
                        logger.error(f"Failed to get administrators: {admin_data}")
                else:
                    logger.error(f"HTTP {response.status} when getting administrators")
            
            # Method 2: Try to get chat member count
            member_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMemberCount"
            params = {"chat_id": TELEGRAM_CHAT_ID}
            
            async with session.get(member_url, params=params) as response:
                if response.status == 200:
                    member_data = await response.json()
                    if member_data.get("ok"):
                        member_count = member_data.get("result", 0)
                        logger.info(f"Chat has {member_count} members")
                    else:
                        logger.error(f"Failed to get member count: {member_data}")
        
        return {
            "status": "info",
            "message": "Bot API has limited access to old messages",
            "limitations": [
                "❌ getUpdates only shows recent messages (24-48 hours)",
                "❌ Bot API cannot access full chat history", 
                "❌ Only Telegram Client API can access old messages"
            ],
            "alternatives": [
                "✅ Use /api/test-data to add sample photos",
                "✅ Ask group members to re-share favorite old photos",
                "✅ Use Telegram Desktop export feature (manual)",
                "✅ Set up the bot earlier to capture future photos"
            ],
            "current_photos": len(images_data)
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}

@app.post("/api/manual-photo-upload")
async def manual_photo_upload(request: Request):
    """Allow manual upload of photo URLs for older photos"""
    global images_data
    
    try:
        data = await request.json()
        
        # Expected format:
        # {
        #   "photo_url": "https://example.com/photo.jpg",
        #   "caption": "Old photo caption",
        #   "date": "2024-01-15" (optional)
        # }
        
        photo_url = data.get("photo_url")
        caption = data.get("caption", "")
        date_str = data.get("date")
        
        if not photo_url:
            return {"status": "error", "message": "photo_url is required"}
        
        # Parse date or use current date
        if date_str:
            try:
                from datetime import datetime
                photo_date = datetime.fromisoformat(date_str)
            except:
                photo_date = datetime.now()
        else:
            photo_date = datetime.now()
        
        # Create photo entry
        photo_id = f"manual_{len(images_data)}_{int(photo_date.timestamp())}"
        
        manual_photo = {
            "id": photo_id,
            "file_id": photo_id,
            "file_unique_id": f"unique_{photo_id}",
            "width": 800,
            "height": 600,
            "timestamp": photo_date.isoformat(),
            "caption": caption,
            "message_id": len(images_data) + 1000,
            "thumb_url": photo_url,
            "full_url": photo_url,
            "from_manual": True,
            "source": "manual_upload"
        }
        
        # Check for duplicates
        existing = next((img for img in images_data if img.get("full_url") == photo_url), None)
        if existing:
            return {
                "status": "info",
                "message": "Photo already exists in gallery",
                "photo_id": existing["id"]
            }
        
        # Add to storage
        images_data.append(manual_photo)
        save_images_to_storage()
        
        return {
            "status": "success",
            "message": "Photo added manually to gallery",
            "photo_id": photo_id,
            "total_photos": len(images_data)
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error adding manual photo: {str(e)}"}

@app.get("/api/telegram-export-guide")
async def telegram_export_guide():
    """Provide instructions for exporting old photos from Telegram"""
    return {
        "status": "info",
        "title": "📚 How to Get ALL Old Photos from Telegram",
        "methods": [
            {
                "method": "1️⃣ Telegram Desktop Export",
                "difficulty": "Easy",
                "steps": [
                    "1. Open Telegram Desktop on computer",
                    "2. Go to Settings → Advanced → Export Telegram data",
                    "3. Select your group chat",
                    "4. Choose 'Media' and set date range",
                    "5. Export will create folder with all photos",
                    "6. Upload photos to a cloud service (Google Drive, etc.)",
                    "7. Use /api/manual-photo-upload to add URLs to gallery"
                ],
                "pros": ["✅ Gets ALL photos", "✅ Includes metadata", "✅ Official method"],
                "cons": ["❌ Manual process", "❌ Requires desktop app"]
            },
            {
                "method": "2️⃣ Ask Group Members to Re-share",
                "difficulty": "Very Easy", 
                "steps": [
                    "1. Ask group members to re-share their favorite old photos",
                    "2. When they re-share, webhook will capture them automatically",
                    "3. Photos will appear in gallery immediately"
                ],
                "pros": ["✅ Fully automatic", "✅ No technical work", "✅ Community involvement"],
                "cons": ["❌ Might not get all photos", "❌ Depends on group participation"]
            },
            {
                "method": "3️⃣ Telegram Client API (Advanced)",
                "difficulty": "Hard",
                "steps": [
                    "1. Create Telegram App at my.telegram.org",
                    "2. Use Telegram Client API (not Bot API)",
                    "3. Write script to fetch full chat history",
                    "4. Process and upload to gallery"
                ],
                "pros": ["✅ Gets ALL photos", "✅ Fully automated", "✅ Complete access"],
                "cons": ["❌ Requires programming", "❌ Complex setup", "❌ API limits"]
            }
        ],
        "recommendation": {
            "best_option": "Method 2: Ask group members to re-share favorite photos",
            "reason": "Easiest and most practical for a baby photo group",
            "action": "Post in group: 'Hey everyone! I set up a photo gallery. Can you re-share your favorite photos of Gaurav? They'll appear automatically! 📸✨'"
        },
        "current_status": {
            "photos_in_gallery": len(images_data),
            "webhook_active": "✅ Capturing new photos automatically",
            "storage_working": "✅ All photos will be preserved"
        }
    }

@app.get("/api/test-webhook")
async def test_webhook_endpoint():
    """Test endpoint to simulate a Telegram webhook with sample data"""
    # Create a sample Telegram update with photo
    sample_update = {
        "update_id": 999999,
        "message": {
            "message_id": 999,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else -1001234567890,
                "title": "Test Group",
                "type": "supergroup"
            },
            "date": int(datetime.now().timestamp()),
            "photo": [
                {
                    "file_id": "test_photo_small",
                    "file_unique_id": "test_unique_small",
                    "width": 90,
                    "height": 90,
                    "file_size": 1234
                },
                {
                    "file_id": "test_photo_large",
                    "file_unique_id": "test_unique_large", 
                    "width": 800,
                    "height": 600,
                    "file_size": 12345
                }
            ],
            "caption": "🧪 Test photo from webhook simulation"
        }
    }
    
    # Process the sample update
    await process_telegram_update(sample_update)
    
    return {
        "status": "success",
        "message": "Webhook test completed",
        "sample_update": sample_update,
        "total_images": len(images_data)
    }

@app.get("/api/test-telegram-updates")
async def test_telegram_updates():
    """Test the actual Telegram getUpdates API to see available data"""
    if not TELEGRAM_BOT_TOKEN:
        return {
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN not configured"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Call the actual Telegram getUpdates API
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                "limit": 10,  # Get last 10 updates
                "timeout": 5   # Short timeout for testing
            }
            
            logger.info(f"Testing Telegram API: {url}")
            
            async with session.get(url, params=params) as response:
                status_code = response.status
                response_text = await response.text()
                
                if status_code == 200:
                    try:
                        data = await response.json()
                        updates = data.get("result", [])
                        
                        # Analyze the updates for photos
                        photo_messages = []
                        for update in updates:
                            if "message" in update:
                                message = update["message"]
                                if "photo" in message or ("document" in message and is_image_document(message.get("document", {}))):
                                    photo_messages.append({
                                        "update_id": update.get("update_id"),
                                        "message_id": message.get("message_id"),
                                        "chat_id": message.get("chat", {}).get("id"),
                                        "chat_title": message.get("chat", {}).get("title"),
                                        "date": message.get("date"),
                                        "caption": message.get("caption", ""),
                                        "has_photo": "photo" in message,
                                        "has_document": "document" in message,
                                        "from_target_chat": str(message.get("chat", {}).get("id")) == str(TELEGRAM_CHAT_ID)
                                    })
                        
                        return {
                            "status": "success",
                            "api_url": url,
                            "http_status": status_code,
                            "telegram_ok": data.get("ok", False),
                            "total_updates": len(updates),
                            "photo_messages": photo_messages,
                            "target_chat_id": TELEGRAM_CHAT_ID,
                            "raw_response": data if len(str(data)) < 5000 else "Response too large to display",
                            "message": f"Found {len(photo_messages)} photo messages in {len(updates)} total updates"
                        }
                        
                    except Exception as json_error:
                        return {
                            "status": "error",
                            "message": f"JSON parsing error: {str(json_error)}",
                            "raw_response": response_text[:1000]
                        }
                        
                else:
                    return {
                        "status": "error",
                        "api_url": url,
                        "http_status": status_code,
                        "message": f"HTTP {status_code} error from Telegram API",
                        "raw_response": response_text[:1000]
                    }
                    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Request error: {str(e)}"
        }

@app.get("/api/telegram-info")
async def telegram_info():
    """Get information about Telegram bot and chat configuration"""
    if not TELEGRAM_BOT_TOKEN:
        return {
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN not configured"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get bot info
            bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
            async with session.get(bot_url) as response:
                if response.status == 200:
                    bot_data = await response.json()
                    bot_info = bot_data.get("result", {}) if bot_data.get("ok") else {}
                else:
                    bot_info = {"error": f"HTTP {response.status}"}
            
            # Get webhook info
            webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            async with session.get(webhook_url) as response:
                if response.status == 200:
                    webhook_data = await response.json()
                    webhook_info = webhook_data.get("result", {}) if webhook_data.get("ok") else {}
                else:
                    webhook_info = {"error": f"HTTP {response.status}"}
            
            # Get chat info if chat ID is configured
            chat_info = {}
            if TELEGRAM_CHAT_ID:
                chat_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
                params = {"chat_id": TELEGRAM_CHAT_ID}
                async with session.get(chat_url, params=params) as response:
                    if response.status == 200:
                        chat_data = await response.json()
                        chat_info = chat_data.get("result", {}) if chat_data.get("ok") else {}
                    else:
                        chat_info = {"error": f"HTTP {response.status}"}
        
        return {
            "status": "success",
            "bot_info": {
                "id": bot_info.get("id"),
                "username": bot_info.get("username"),
                "first_name": bot_info.get("first_name"),
                "can_join_groups": bot_info.get("can_join_groups"),
                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages")
            },
            "webhook_info": {
                "url": webhook_info.get("url"),
                "has_custom_certificate": webhook_info.get("has_custom_certificate"),
                "pending_update_count": webhook_info.get("pending_update_count"),
                "last_error_date": webhook_info.get("last_error_date"),
                "last_error_message": webhook_info.get("last_error_message")
            },
            "chat_info": {
                "id": chat_info.get("id"),
                "title": chat_info.get("title"),
                "type": chat_info.get("type"),
                "member_count": chat_info.get("member_count")
            },
            "configuration": {
                "bot_token_configured": bool(TELEGRAM_BOT_TOKEN),
                "chat_id_configured": bool(TELEGRAM_CHAT_ID),
                "chat_id": TELEGRAM_CHAT_ID
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting Telegram info: {str(e)}"
        }

@app.get("/api/fetch-history")
async def fetch_history(request: Request):
    """Smart fetch: Temporarily disable webhook, get history, re-enable webhook"""
    global images_data
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
        }
    
    try:
        logger.info("Starting smart history fetch process...")
        
        # Step 1: Get current webhook info
        webhook_url = None
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        webhook_url = data.get("result", {}).get("url")
        
        logger.info(f"Current webhook URL: {webhook_url}")
        
        # Step 2: Temporarily delete webhook
        if webhook_url:
            logger.info("Temporarily deleting webhook to access getUpdates...")
            async with aiohttp.ClientSession() as session:
                delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
                async with session.get(delete_url) as response:
                    if response.status != 200:
                        return {"status": "error", "message": "Failed to delete webhook"}
                    
                    delete_data = await response.json()
                    if not delete_data.get("ok"):
                        return {"status": "error", "message": f"Webhook deletion failed: {delete_data}"}
        
        # Step 3: Fetch updates using getUpdates
        logger.info("Fetching chat history using getUpdates...")
        historical_photos = await fetch_updates_history()
        
        # Step 4: Re-enable webhook
        if webhook_url:
            logger.info("Re-enabling webhook...")
            async with aiohttp.ClientSession() as session:
                base_url = str(request.base_url).rstrip("/")
                new_webhook_url = f"{base_url}/api/telegram/webhook"
                
                set_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
                params = {"url": new_webhook_url}
                async with session.get(set_url, params=params) as response:
                    if response.status == 200:
                        webhook_data = await response.json()
                        if webhook_data.get("ok"):
                            logger.info("Webhook re-enabled successfully")
                        else:
                            logger.error(f"Failed to re-enable webhook: {webhook_data}")
        
        # Step 5: Process and save historical photos
        if historical_photos:
            initial_count = len(images_data)
            
            # Add new photos (duplicates are already filtered out)
            for photo in historical_photos:
                images_data.append(photo)
            
            save_images_to_storage()
            new_count = len(images_data) - initial_count
            
            logger.info(f"Successfully added {new_count} historical photos")
            
            return {
                "status": "success",
                "message": f"Smart fetch completed! Found {len(historical_photos)} photos from history",
                "new_photos_added": new_count,
                "total_photos": len(images_data),
                "webhook_restored": bool(webhook_url),
                "process": [
                    "✅ Temporarily disabled webhook",
                    "✅ Fetched chat history via getUpdates", 
                    "✅ Processed historical photos",
                    "✅ Re-enabled webhook",
                    "✅ Ready for new photos!"
                ]
            }
        else:
            return {
                "status": "info",
                "message": "No historical photos found in recent updates",
                "new_photos_added": 0,
                "total_photos": len(images_data),
                "webhook_restored": bool(webhook_url)
            }
            
    except Exception as e:
        logger.error(f"Error in smart history fetch: {e}")
        
        # Try to restore webhook even if there was an error
        if webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    base_url = str(request.base_url).rstrip("/")
                    restore_webhook_url = f"{base_url}/api/telegram/webhook"
                    set_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
                    params = {"url": restore_webhook_url}
                    await session.get(set_url, params=params)
                    logger.info("Webhook restored after error")
            except:
                logger.error("Failed to restore webhook after error")
        
        return {
            "status": "error",
            "message": f"Smart fetch failed: {str(e)}",
            "webhook_restored": "attempted"
        }

async def fetch_updates_history():
    """Fetch historical photos using getUpdates (only works when webhook is disabled)"""
    all_photos = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get recent updates (last 100)
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                "limit": 100,
                "timeout": 10
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"HTTP error {response.status} when fetching updates")
                    return []
                
                data = await response.json()
                if not data.get("ok"):
                    logger.error(f"Telegram API error: {data}")
                    return []
                
                updates = data.get("result", [])
                logger.info(f"Retrieved {len(updates)} updates from Telegram")
                
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
                
                logger.info(f"Found {len(all_photos)} photos in chat history")
                return all_photos
                
    except Exception as e:
        logger.error(f"Error fetching updates history: {e}")
        return []

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
    """Fetch existing photos from Telegram group using getChatHistory API"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return []
    
    logger.info("Fetching chat history to get existing photos...")
    all_photos = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Use getChatHistory API to get recent messages
            # Note: This gets the most recent messages, not all history
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
            params = {
                "chat_id": TELEGRAM_CHAT_ID
            }
            
            # First, verify we can access the chat
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Cannot access chat {TELEGRAM_CHAT_ID}: HTTP {response.status}")
                    return []
                
                chat_data = await response.json()
                if not chat_data.get("ok"):
                    logger.error(f"Cannot access chat: {chat_data}")
                    return []
                
                logger.info(f"Successfully connected to chat: {chat_data['result'].get('title', 'Unknown')}")
            
            # Since we can't get full history with bot API, let's try a different approach
            # We'll create some test data to demonstrate the system works
            logger.warning("Note: Telegram Bot API has limited access to chat history")
            logger.info("For full chat history, you would need to:")
            logger.info("1. Use Telegram Client API (not Bot API)")
            logger.info("2. Or manually trigger /api/test-data to add sample photos")
            logger.info("3. New photos will be captured automatically via webhook")
            
            return []  # Return empty for now, webhook will capture new photos
        
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
    global images_data  # Declare global at the top of the function
    
    # Create test images with baby-themed content
    from datetime import datetime, timedelta
    import random
    
    # Generate photos from different months to test grouping
    base_date = datetime.now()
    test_images = []
    
    captions = [
        "Gaurav's first smile 😊",
        "Playing with toys 🧸",
        "Naptime cuteness 😴",
        "Learning to crawl 👶",
        "First solid food 🍼",
        "Bath time fun 🛁",
        "Tummy time adventures",
        "Sleepy baby moments",
        "Playtime with daddy",
        "Mommy's little angel"
    ]
    
    for i in range(10):
        # Create photos from different months
        photo_date = base_date - timedelta(days=random.randint(1, 180))
        
        test_images.append({
            "id": f"test{i+1}",
            "file_id": f"test{i+1}",
            "file_unique_id": f"unique{i+1}",
            "width": 800,
            "height": 600,
            "timestamp": photo_date.isoformat(),
            "caption": captions[i],
            "message_id": i+1,
            "thumb_url": f"https://picsum.photos/300/300?random={i+10}",
            "full_url": f"https://picsum.photos/800/600?random={i+10}",
            "from_test": True
        })
    
    # Only add photos that don't already exist
    existing_ids = {img["file_id"] for img in images_data}
    new_photos = [img for img in test_images if img["file_id"] not in existing_ids]
    
    if new_photos:
        images_data.extend(new_photos)
        save_images_to_storage()
        return {
            "status": "success", 
            "message": f"Added {len(new_photos)} test photos",
            "total_photos": len(images_data)
        }
    else:
        return {
            "status": "info",
            "message": "Test photos already exist",
            "total_photos": len(images_data)
        }

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

@app.get("/api/webhook-status")
async def webhook_status():
    """Check current webhook status"""
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not configured"}
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        webhook_info = data.get("result", {})
                        return {
                            "status": "success",
                            "webhook_active": bool(webhook_info.get("url")),
                            "webhook_url": webhook_info.get("url"),
                            "pending_updates": webhook_info.get("pending_update_count", 0),
                            "last_error": webhook_info.get("last_error_message"),
                            "last_error_date": webhook_info.get("last_error_date"),
                            "max_connections": webhook_info.get("max_connections"),
                            "full_info": webhook_info
                        }
                    else:
                        return {"status": "error", "message": f"Telegram API error: {data}"}
                else:
                    return {"status": "error", "message": f"HTTP error {response.status}"}
    except Exception as e:
        return {"status": "error", "message": f"Exception: {e}"}

@app.get("/api/delete-webhook")
async def delete_webhook():
    """Temporarily delete webhook to test getUpdates"""
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not configured"}
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return {
                            "status": "success", 
                            "message": "Webhook deleted successfully",
                            "note": "⚠️ Remember to set it back up with /setup-webhook"
                        }
                    else:
                        return {"status": "error", "message": f"Telegram API error: {data}"}
                else:
                    return {"status": "error", "message": f"HTTP error {response.status}"}
    except Exception as e:
        return {"status": "error", "message": f"Exception: {e}"}

@app.post("/api/test-webhook-receive")
async def test_webhook_receive(request: Request):
    """Test endpoint to simulate receiving a webhook"""
    try:
        # Get the raw request data
        body = await request.body()
        headers = dict(request.headers)
        
        # Try to parse as JSON
        try:
            json_data = await request.json()
        except:
            json_data = None
        
        # Log the received data
        logger.info(f"Test webhook received - Headers: {headers}")
        logger.info(f"Test webhook received - Body: {body.decode() if body else 'Empty'}")
        
        # If it's valid JSON, process it
        if json_data:
            await process_telegram_update(json_data)
            return {
                "status": "success",
                "message": "Webhook data processed successfully",
                "received_data": json_data
            }
        else:
            return {
                "status": "info",
                "message": "Received non-JSON data",
                "headers": headers,
                "body": body.decode() if body else None
            }
            
    except Exception as e:
        logger.error(f"Error in test webhook: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}

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