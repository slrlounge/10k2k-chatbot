#!/usr/bin/env python3
"""
Google Drive Sync Script using PyDrive2
Downloads all PDFs and MP4s from a specified Google Drive folder.
No manual login required after first setup.
"""

import os
import sys
from pathlib import Path
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Folder ID from the Google Drive URL
DRIVE_FOLDER_ID = '1QBLmy7mMHf0SCzqFdKOp3-vsaavRWD-2'

# Local directories - can be overridden via environment variables
SOURCE_DATA_DIR = Path(os.getenv('SOURCE_DATA_DIR', 'data'))
PDF_DIR = Path(os.getenv('PDF_DIR', str(SOURCE_DATA_DIR / 'pdfs')))
VIDEO_DIR = Path(os.getenv('VIDEO_DIR', str(SOURCE_DATA_DIR / 'videos')))

# Supported file types
PDF_MIME_TYPE = 'application/pdf'
MP4_MIME_TYPE = 'video/mp4'


def authenticate() -> GoogleDrive:
    """Authenticate with Google Drive API using PyDrive2."""
    gauth = GoogleAuth()
    
    # Try to load saved client credentials
    settings_file = Path('settings.yaml')
    if not settings_file.exists():
        print("ERROR: settings.yaml not found!")
        print("\nPlease create settings.yaml with the following content:")
        print("""
client_config_backend: settings
client_config:
  client_id: YOUR_CLIENT_ID.apps.googleusercontent.com
  client_secret: YOUR_CLIENT_SECRET
save_credentials: True
save_credentials_backend: file
save_credentials_file: credentials.json
get_refresh_token: True

# Optional: Use service account instead
# service_config:
#   client_user_email: YOUR_SERVICE_ACCOUNT_EMAIL
# service_account_file: service_account.json
""")
        print("\nTo get credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select existing one")
        print("3. Enable Google Drive API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Create settings.yaml with your credentials")
        sys.exit(1)
    
    # Try to load saved client credentials
    credentials_file = Path('credentials.json')
    if credentials_file.exists():
        gauth.LoadCredentialsFile(str(credentials_file))
    
    # Authenticate if credentials are invalid or missing
    if gauth.credentials is None:
        # Authenticate and save credentials
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile(str(credentials_file))
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
        gauth.SaveCredentialsFile(str(credentials_file))
    else:
        # Initialize the saved creds
        gauth.Authorize()
    
    # Create GoogleDrive instance
    drive = GoogleDrive(gauth)
    return drive


def get_all_files_in_folder(drive: GoogleDrive, folder_id: str) -> list:
    """Recursively get all files in a Google Drive folder and subfolders."""
    all_files = []
    
    def list_files_in_folder(folder_id: str):
        """List files in a specific folder."""
        try:
            # List files in the folder
            file_list = drive.ListFile({
                'q': f"'{folder_id}' in parents and trashed=false"
            }).GetList()
            
            for file_item in file_list:
                mime_type = file_item.get('mimeType', '')
                
                # If it's a folder, recurse into it
                if mime_type == 'application/vnd.google-apps.folder':
                    list_files_in_folder(file_item['id'])
                else:
                    # It's a file, add to our list
                    all_files.append(file_item)
                    
        except Exception as e:
            print(f"Error listing files in folder {folder_id}: {e}")
    
    list_files_in_folder(folder_id)
    return all_files


def download_file(drive: GoogleDrive, file_item, destination: Path) -> bool:
    """Download a file from Google Drive."""
    try:
        file_name = file_item['title']
        file_path = destination / file_name
        
        # Create destination directory if it doesn't exist
        destination.mkdir(parents=True, exist_ok=True)
        
        # Download the file with progress
        print(f"  Downloading: {file_name}...", end='', flush=True)
        file_item.GetContentFile(str(file_path))
        print(f" ✓")
        return True
        
    except Exception as e:
        print(f" ✗ Error: {e}")
        return False


def main():
    """Main function to sync files from Google Drive."""
    print("Google Drive Sync Script (PyDrive2)")
    print("=" * 50)
    
    # Ensure directories exist
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Authenticate
    print("\n[1/3] Authenticating with Google Drive API...")
    try:
        drive = authenticate()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)
    
    # Get all files in the folder
    print(f"\n[2/3] Scanning folder {DRIVE_FOLDER_ID}...")
    try:
        all_files = get_all_files_in_folder(drive, DRIVE_FOLDER_ID)
        print(f"✓ Found {len(all_files)} files total")
    except Exception as e:
        print(f"✗ Error scanning folder: {e}")
        sys.exit(1)
    
    # Filter PDFs and MP4s
    pdf_files = [f for f in all_files if f.get('mimeType') == PDF_MIME_TYPE]
    mp4_files = [f for f in all_files if f.get('mimeType') == MP4_MIME_TYPE]
    
    print(f"\nFound {len(pdf_files)} PDF files and {len(mp4_files)} MP4 files")
    
    # Download PDFs
    if pdf_files:
        print(f"\n[3/3] Processing {len(pdf_files)} PDF files...")
        downloaded = 0
        skipped = 0
        
        for file_item in pdf_files:
            file_name = file_item['title']
            file_path = PDF_DIR / file_name
            
            if file_path.exists():
                print(f"  ⊘ Skipped (exists): {file_name}")
                skipped += 1
            else:
                if download_file(drive, file_item, PDF_DIR):
                    downloaded += 1
        
        print(f"\nPDFs: {downloaded} downloaded, {skipped} skipped")
    
    # Download MP4s
    if mp4_files:
        print(f"\n[3/3] Processing {len(mp4_files)} MP4 files...")
        downloaded = 0
        skipped = 0
        
        for file_item in mp4_files:
            file_name = file_item['title']
            file_path = VIDEO_DIR / file_name
            
            if file_path.exists():
                print(f"  ⊘ Skipped (exists): {file_name}")
                skipped += 1
            else:
                if download_file(drive, file_item, VIDEO_DIR):
                    downloaded += 1
        
        print(f"\nMP4s: {downloaded} downloaded, {skipped} skipped")
    
    print("\n" + "=" * 50)
    print("Sync complete!")


if __name__ == '__main__':
    main()
