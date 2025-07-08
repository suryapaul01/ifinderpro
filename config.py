import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [id.strip() for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]  # Comma-separated list of admin user IDs
TON_WALLET = os.getenv('TON_WALLET', '')  # TON wallet address for donations 