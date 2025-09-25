from supabase import create_client, Client
import os
from dotenv import load_dotenv
from pathlib import Path

# Get the directory where this file is located
current_dir = Path(__file__).parent
# Go up to the app directory and load .env from there
env_path = current_dir.parent / '.env'
load_dotenv(env_path)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")

print(f"Connecting to Supabase at {url} with key {key}")

supabase: Client = create_client(url, key)

def get_supabase_client() -> Client:
    return supabase