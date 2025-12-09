"""
Upload all files from GCS bucket to Gemini File Search Store
This script will upload all files from gs://slr-rag-gemini to your File Search Store
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client

load_dotenv()

BUCKET_NAME = "slr-rag-gemini"

def get_gcs_files(bucket_name):
    """Get list of all files in GCS bucket"""
    print(f"📦 Listing files in gs://{bucket_name}...")
    
    try:
        result = subprocess.run(
            ["gsutil", "ls", "-r", f"gs://{bucket_name}/**"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Error listing files: {result.stderr}")
            return []
        
        files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip() and not line.endswith('/')]
        print(f"✅ Found {len(files)} files")
        return files
        
    except FileNotFoundError:
        print("❌ gsutil not found. Please install Google Cloud SDK:")
        print("   https://cloud.google.com/sdk/docs/install")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def upload_file_to_gemini(gcs_uri, client):
    """Upload a single file from GCS to Gemini Files"""
    try:
        # Upload file from GCS URI
        file = client.files.upload(
            file=gcs_uri,
            config={
                "display_name": Path(gcs_uri).name
            }
        )
        return file.name
    except Exception as e:
        print(f"   ⚠️  Error uploading {gcs_uri}: {e}")
        return None

def add_file_to_store(store_id, file_name, client):
    """Add a file to the File Search Store"""
    try:
        client.file_search_stores.files.create(
            file_search_store=store_id,
            file=file_name
        )
        return True
    except Exception as e:
        print(f"   ⚠️  Error adding to store: {e}")
        return False

def main():
    print("="*70)
    print("  UPLOAD FILES FROM GCS TO FILE SEARCH STORE")
    print("="*70)
    
    # Check environment
    api_key = os.getenv("GEMINI_API_KEY", "")
    store_id = os.getenv("GEMINI_STORE_ID", "")
    
    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)
    
    if not store_id or store_id == "your_file_search_store_id_here":
        print("❌ GEMINI_STORE_ID not set in .env")
        print("   Run: python create_store.py")
        sys.exit(1)
    
    # Initialize client
    try:
        client = Client()
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        sys.exit(1)
    
    # Get files from GCS
    gcs_files = get_gcs_files(BUCKET_NAME)
    
    if not gcs_files:
        print("❌ No files found or error listing files")
        sys.exit(1)
    
    print(f"\n📤 Uploading {len(gcs_files)} files to File Search Store...")
    print("="*70)
    
    uploaded = 0
    failed = 0
    already_in_store = 0
    
    # Get existing files in store
    try:
        store_files = client.file_search_stores.files.list(file_search_store=store_id)
        existing_file_names = {f.file.name for f in store_files}
        print(f"📋 Found {len(existing_file_names)} files already in store")
    except:
        existing_file_names = set()
    
    for i, gcs_uri in enumerate(gcs_files, 1):
        file_name = Path(gcs_uri).name
        print(f"\n[{i}/{len(gcs_files)}] Processing: {file_name}")
        
        # Check if already uploaded
        if file_name in existing_file_names:
            print(f"   ⏭️  Already in store, skipping")
            already_in_store += 1
            continue
        
        # Upload to Gemini Files
        gemini_file_name = upload_file_to_gemini(gcs_uri, client)
        if not gemini_file_name:
            failed += 1
            continue
        
        print(f"   ✅ Uploaded to Gemini Files")
        
        # Add to File Search Store
        if add_file_to_store(store_id, gemini_file_name, client):
            print(f"   ✅ Added to File Search Store")
            uploaded += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    print("  UPLOAD SUMMARY")
    print("="*70)
    print(f"✅ Successfully uploaded: {uploaded}")
    print(f"⏭️  Already in store: {already_in_store}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total processed: {len(gcs_files)}")
    
    if uploaded > 0:
        print("\n✅ Files are now available in your File Search Store!")
        print("   You can now test your chatbot.")

if __name__ == "__main__":
    main()


