"""
Create File Search Store using REST API directly
This is an alternative if the SDK method doesn't work
"""
import os
import json
import requests

# Read API key from .env
api_key = None
try:
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
except:
    pass

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY", "")

if not api_key:
    print("❌ GEMINI_API_KEY not found")
    print("   Please set it in .env file or environment variable")
    exit(1)

# Create File Search Store via REST API
url = "https://generativelanguage.googleapis.com/v1beta/fileSearchStores"

headers = {
    "Content-Type": "application/json"
}

params = {
    "key": api_key
}

data = {
    "displayName": "Kajabi_Knowledge_Base"
}

print("Creating File Search Store via REST API...")
print(f"Store Name: {data['displayName']}")

try:
    response = requests.post(url, headers=headers, params=params, json=data)
    
    if response.status_code == 200:
        result = response.json()
        store_id = result.get("name", "")
        print("\n" + "="*60)
        print("✅ SUCCESS: File Search Store Created!")
        print("="*60)
        print(f"Store Name: {data['displayName']}")
        print(f"Store ID:   {store_id}")
        print("="*60)
        print("\n📝 Next: Add this Store ID to your .env file:")
        print(f"   GEMINI_STORE_ID={store_id}")
    else:
        print(f"\n❌ Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 404:
            print("\n💡 Tip: File Search API might not be available in your region")
            print("   Try creating it via Google AI Studio instead:")
            print("   https://aistudio.google.com/")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Alternative: Create the store via Google AI Studio:")
    print("   1. Go to https://aistudio.google.com/")
    print("   2. Navigate to File Search")
    print("   3. Create a new store named 'Kajabi_Knowledge_Base'")
    print("   4. Copy the Store ID and add it to .env")

