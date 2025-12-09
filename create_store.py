import os
import time
import sys
from google.genai import Client

# 1. Initialize the Client
# Try to get API key from environment variable or .env file
api_key = os.getenv("GEMINI_API_KEY", "")

# If not in environment, try reading from .env file
if not api_key:
    try:
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    except:
        pass

if not api_key:
    print("FATAL: GEMINI_API_KEY not found in environment variables or .env file")
    sys.exit(1)

try:
    client = Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing client: {e}")
    print("FATAL: Please ensure your GEMINI_API_KEY is set correctly.")
    sys.exit(1)

# 2. Create the File Search Store (The Index Container)
store_name = "Kajabi_Knowledge_Base"
print(f"Attempting to create File Search Store: {store_name}...")

try:
    # Check if a store with this display name already exists
    existing_stores = client.file_search_stores.list()
    for store in existing_stores:
        if store.display_name == store_name:
            print(f"Store already exists! ID: {store.name}")
            print("Using existing store. Skipping creation.")
            sys.exit(0) 

    # If it doesn't exist, create it
    file_search_store = client.file_search_stores.create(
        config={"display_name": store_name}
    )

    store_id = file_search_store.name 
    print("\n-------------------------------------------------------")
    print("           ✅ SUCCESS: File Search Store Created!")
    print(f"Store Name: {store_name}")
    print(f"Store ID:   {store_id}")
    print("-------------------------------------------------------")
    print("CRUCIAL: Copy this Store ID. It's needed for ALL future steps.")

except Exception as e:
    print(f"\nFATAL: An error occurred while creating the store: {e}")
    print("Ensure you have linked your project to the API key in Google AI Studio.")
    sys.exit(1)
