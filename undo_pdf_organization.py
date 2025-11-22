#!/usr/bin/env python3
"""
Undo PDF chunk organization - move files back from PDF subfolders to parent directories.
"""

import os
import shutil
from pathlib import Path

SOURCE_DIR = Path('/Users/justinlin/Documents/10K2KChatBot/10K2Kv2')

stats = {
    'files_found': 0,
    'files_moved': 0,
    'folders_removed': 0,
    'errors': 0
}


def undo_organization():
    """Move all files from PDF subfolders back to parent directories."""
    print("=" * 70)
    print("UNDOING PDF CHUNK ORGANIZATION")
    print("=" * 70)
    print(f"Source directory: {SOURCE_DIR}")
    print()
    
    # Find all PDF subfolders
    print("Searching for PDF subfolders...")
    pdf_folders = []
    
    for pdf_folder in SOURCE_DIR.rglob("PDF"):
        if pdf_folder.is_dir():
            pdf_folders.append(pdf_folder)
    
    if not pdf_folders:
        print("✗ No PDF subfolders found!")
        return
    
    print(f"✓ Found {len(pdf_folders)} PDF subfolder(s)")
    print()
    
    # Move files back to parent directories
    print("Moving files back to parent directories...")
    print()
    
    for pdf_folder in sorted(pdf_folders):
        parent_dir = pdf_folder.parent
        
        # Get all files in PDF folder
        files_in_pdf = list(pdf_folder.glob("*"))
        txt_files = [f for f in files_in_pdf if f.is_file() and f.suffix == '.txt']
        
        if not txt_files:
            print(f"No files in {pdf_folder}")
            continue
        
        print(f"Processing: {pdf_folder}")
        print(f"  Parent: {parent_dir}")
        print(f"  Files found: {len(txt_files)}")
        
        # Move each file back to parent
        for txt_file in sorted(txt_files):
            try:
                dest_path = parent_dir / txt_file.name
                # Check if file already exists in parent
                if dest_path.exists():
                    print(f"    ⚠ Skipping {txt_file.name} (already exists in parent)")
                    stats['errors'] += 1
                    continue
                
                shutil.move(str(txt_file), str(dest_path))
                print(f"    ✓ Moved: {txt_file.name}")
                stats['files_moved'] += 1
                stats['files_found'] += 1
            except Exception as e:
                print(f"    ✗ Error moving {txt_file.name}: {e}")
                stats['errors'] += 1
        
        # Remove PDF folder if empty
        try:
            remaining_files = list(pdf_folder.glob("*"))
            if not remaining_files:
                pdf_folder.rmdir()
                print(f"  ✓ Removed empty PDF folder")
                stats['folders_removed'] += 1
            else:
                print(f"  ⚠ PDF folder not empty, keeping it")
        except Exception as e:
            print(f"  ✗ Error removing PDF folder: {e}")
        
        print()
    
    # Print summary
    print("=" * 70)
    print("UNDO SUMMARY")
    print("=" * 70)
    print(f"Files found: {stats['files_found']}")
    print(f"Files moved: {stats['files_moved']}")
    print(f"PDF folders removed: {stats['folders_removed']}")
    print(f"Errors: {stats['errors']}")
    print()
    print("=" * 70)
    print("✓ UNDO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    undo_organization()

