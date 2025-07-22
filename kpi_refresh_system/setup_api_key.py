#!/usr/bin/env python3
"""
Secure API Key Setup Script
This helps you store your API key securely on your local machine
"""

import os
import sys
from pathlib import Path
import getpass

def setup_api_key():
    print("=" * 60)
    print("CANALYST API KEY SETUP")
    print("=" * 60)
    print("\nThis script will help you securely store your API key locally.")
    print("The key will be stored in a .env file that is NOT tracked by git.\n")
    
    # Check if .env already exists
    env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        print("WARNING: A .env file already exists.")
        response = input("Do you want to update the API key? (y/n): ").lower()
        if response != 'y':
            print("Setup cancelled.")
            return
    
    # Get API key securely (hides input)
    print("\nPlease enter your Canalyst API token.")
    print("(Your input will be hidden for security)")
    api_key = getpass.getpass("API Token: ").strip()
    
    if not api_key:
        print("ERROR: No API key provided. Setup cancelled.")
        return
    
    # Validate it looks like a token
    if len(api_key) < 20:
        print("ERROR: That doesn't look like a valid API token (too short).")
        print("   Please check you've copied the entire token.")
        return
    
    # Write to .env file
    try:
        with open(env_path, 'w') as f:
            f.write(f"CANALYST_API_TOKEN={api_key}\n")
        
        print("\nSUCCESS: API key saved successfully to .env file!")
        print("\nImportant reminders:")
        print("   - This .env file is NOT tracked by git (safe)")
        print("   - Keep your API key secret and never commit it")
        print("   - Each team member needs to run this script locally")
        print("\nYou can now run the application!")
        
    except Exception as e:
        print(f"\nERROR: Error saving API key: {e}")
        return

if __name__ == "__main__":
    setup_api_key()