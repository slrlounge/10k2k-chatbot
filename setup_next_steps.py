"""
Next Steps Setup Script
This script will guide you through connecting your GCS bucket to Gemini FileSearch
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client

def print_step(step_num, title):
    print("\n" + "="*70)
    print(f"STEP {step_num}: {title}")
    print("="*70)

def check_env_file():
    """Check if .env file exists and has required values"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  .env file not found. Creating from template...")
        env_example = Path("env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ Created .env file. Please edit it with your values.")
            return False
        else:
            print("❌ env.example not found. Cannot create .env")
            return False
    
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    store_id = os.getenv("GEMINI_STORE_ID", "")
    
    if not api_key or api_key == "your_gemini_api_key_here":
        print("⚠️  GEMINI_API_KEY not set in .env")
        print("   Please add your API key from Google AI Studio")
        return False
    
    print(f"✅ GEMINI_API_KEY is set (length: {len(api_key)})")
    
    if not store_id or store_id == "your_file_search_store_id_here":
        print("⚠️  GEMINI_STORE_ID not set in .env")
        print("   We'll create the store in the next step")
        return "no_store"
    
    print(f"✅ GEMINI_STORE_ID is set: {store_id[:30]}...")
    return True

def create_file_search_store():
    """Create or verify File Search Store exists"""
    print_step(1, "Create File Search Store")
    
    try:
        client = Client()
    except Exception as e:
        print(f"❌ Error initializing Gemini client: {e}")
        print("   Make sure GEMINI_API_KEY is set in .env")
        return None
    
    store_name = "Kajabi_Knowledge_Base"
    print(f"Looking for store: {store_name}")
    
    try:
        # Check existing stores
        existing_stores = client.file_search_stores.list()
        for store in existing_stores:
            if store.display_name == store_name:
                store_id = store.name
                print(f"✅ Store already exists!")
                print(f"   Store ID: {store_id}")
                return store_id
        
        # Create new store
        print("Creating new File Search Store...")
        file_search_store = client.file_search_stores.create(
            config={"display_name": store_name}
        )
        store_id = file_search_store.name
        print(f"✅ Store created successfully!")
        print(f"   Store ID: {store_id}")
        
        # Update .env file
        update_env_file("GEMINI_STORE_ID", store_id)
        print(f"✅ Updated .env file with Store ID")
        
        return store_id
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def update_env_file(key, value):
    """Update a key in .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        return
    
    lines = []
    updated = False
    
    with open(env_file, 'r') as f:
        for line in f:
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                updated = True
            else:
                lines.append(line)
    
    if not updated:
        lines.append(f"{key}={value}\n")
    
    with open(env_file, 'w') as f:
        f.writelines(lines)

def list_gcs_files(bucket_name):
    """List files in GCS bucket (requires gcloud CLI)"""
    print_step(2, f"List Files in GCS Bucket: {bucket_name}")
    
    import subprocess
    
    try:
        # Try using gcloud CLI
        result = subprocess.run(
            ["gsutil", "ls", f"gs://{bucket_name}/**"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            print(f"✅ Found {len(files)} files in bucket")
            return files
        else:
            print("⚠️  gcloud CLI not available or bucket not accessible")
            print("   You can manually list files in Google Cloud Console")
            return None
            
    except FileNotFoundError:
        print("⚠️  gsutil not found. Install Google Cloud SDK or list files manually")
        return None
    except Exception as e:
        print(f"⚠️  Error listing files: {e}")
        return None

def upload_files_to_store(store_id, bucket_name):
    """Upload files from GCS bucket to File Search Store"""
    print_step(3, f"Upload Files from GCS Bucket to File Search Store")
    
    print(f"\n📝 IMPORTANT: There are two ways to add files to File Search Store:")
    print("\n   Option A: Via Google AI Studio (Recommended)")
    print("   1. Go to https://aistudio.google.com/")
    print("   2. Navigate to File Search section")
    print("   3. Select your store")
    print("   4. Click 'Add files' or 'Connect GCS bucket'")
    print("   5. Select your bucket: gs://slr-rag-gemini")
    
    print("\n   Option B: Via API (Programmatic)")
    print("   This requires listing all files and uploading them individually")
    print("   We can create a script to do this if needed")
    
    response = input("\n   Do you want to proceed with Option A (Google AI Studio)? (y/n): ")
    
    if response.lower() == 'y':
        print("\n✅ Please follow the steps above in Google AI Studio")
        print("   Once files are added, you can test the chatbot")
        return True
    else:
        print("\n📝 To upload programmatically, you'll need to:")
        print("   1. List all files in gs://slr-rag-gemini")
        print("   2. Upload each file to Gemini Files API")
        print("   3. Add files to the File Search Store")
        print("\n   Would you like me to create a script for this?")
        return False

def test_setup(store_id):
    """Test the setup"""
    print_step(4, "Test the Setup")
    
    print("To test your chatbot:")
    print("\n1. Start the server:")
    print("   python app.py")
    
    print("\n2. Create a test token:")
    print("   python token_manager.py create test@example.com")
    
    print("\n3. Open browser:")
    print("   http://localhost:8000")
    
    print("\n4. Enter the token and start chatting!")
    
    print("\n✅ Setup complete! Your chatbot is ready to use.")

def main():
    print("\n" + "="*70)
    print("  RAG CHATBOT SETUP - NEXT STEPS")
    print("="*70)
    
    # Step 0: Check environment
    env_status = check_env_file()
    if env_status == False:
        print("\n⚠️  Please edit .env file with your GEMINI_API_KEY first")
        print("   Get your API key from: https://aistudio.google.com/api-keys")
        sys.exit(1)
    
    # Step 1: Create File Search Store
    if env_status == "no_store":
        store_id = create_file_search_store()
        if not store_id:
            print("\n❌ Failed to create store. Please check your API key.")
            sys.exit(1)
    else:
        load_dotenv()
        store_id = os.getenv("GEMINI_STORE_ID")
        print(f"\n✅ Using existing store: {store_id[:30]}...")
    
    # Step 2: List GCS files (optional)
    bucket_name = "slr-rag-gemini"
    files = list_gcs_files(bucket_name)
    
    # Step 3: Upload files to store
    upload_files_to_store(store_id, bucket_name)
    
    # Step 4: Test instructions
    test_setup(store_id)
    
    print("\n" + "="*70)
    print("  SETUP COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()


