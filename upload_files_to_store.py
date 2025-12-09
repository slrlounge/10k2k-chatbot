"""
Upload files from Google Cloud Storage to Gemini File Search Store

This script helps you upload files from your GCS bucket to your File Search Store.
Make sure your files are already in the GCS bucket before running this.
"""
import os
import sys
from dotenv import load_dotenv
from google.genai import Client

load_dotenv()

def upload_files_from_gcs(store_id: str, gcs_uris: list[str]):
    """Upload files from GCS URIs to the File Search Store"""
    try:
        client = Client()
    except Exception as e:
        print(f"Error initializing client: {e}")
        print("FATAL: Please ensure your GEMINI_API_KEY environment variable is set.")
        sys.exit(1)
    
    print(f"Uploading {len(gcs_uris)} files to store: {store_id}")
    print("="*60)
    
    uploaded_files = []
    failed_files = []
    
    for gcs_uri in gcs_uris:
        try:
            print(f"\nUploading: {gcs_uri}")
            
            # Upload file from GCS
            file = client.files.upload(
                file=gcs_uri,
                config={
                    "display_name": os.path.basename(gcs_uri)
                }
            )
            
            print(f"  ✅ Uploaded: {file.name}")
            
            # Add file to store
            client.file_search_stores.files.create(
                file_search_store=store_id,
                file=file.name
            )
            
            print(f"  ✅ Added to store")
            uploaded_files.append(gcs_uri)
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed_files.append((gcs_uri, str(e)))
    
    print("\n" + "="*60)
    print("Upload Summary:")
    print(f"  ✅ Successfully uploaded: {len(uploaded_files)}")
    print(f"  ❌ Failed: {len(failed_files)}")
    
    if failed_files:
        print("\nFailed files:")
        for uri, error in failed_files:
            print(f"  - {uri}: {error}")
    
    return uploaded_files, failed_files


def main():
    store_id = os.getenv("GEMINI_STORE_ID", "")
    
    if not store_id:
        print("Error: GEMINI_STORE_ID not set in environment variables")
        print("Please set it in your .env file or run:")
        print("  export GEMINI_STORE_ID=your_store_id")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python upload_files_to_store.py gs://bucket/file1.pdf gs://bucket/file2.pdf ...")
        print("\nExample:")
        print("  python upload_files_to_store.py gs://my-bucket/docs/file1.pdf gs://my-bucket/docs/file2.pdf")
        sys.exit(1)
    
    gcs_uris = sys.argv[1:]
    
    # Validate GCS URIs
    invalid_uris = [uri for uri in gcs_uris if not uri.startswith("gs://")]
    if invalid_uris:
        print("Error: All URIs must start with 'gs://'")
        print("Invalid URIs:", invalid_uris)
        sys.exit(1)
    
    upload_files_from_gcs(store_id, gcs_uris)


if __name__ == "__main__":
    main()

