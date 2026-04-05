import os
from dotenv import load_dotenv

load_dotenv()
VK_TOKEN = os.getenv("VK_TOKEN")
if not VK_TOKEN:
    raise ValueError("VK_TOKEN not set in environment")
