"""
Helper script to set up Canalyst API authentication
"""

import os
import sys
import getpass

def setup_auth():
    print("\n=== Canalyst API Authentication Setup ===")
    print("=" * 50)
    
    print("\nChoose authentication method:")
    print("1. API Key (recommended)")
    print("2. Username & Password")
    
    choice = input("\nSelect (1 or 2): ").strip()
    
    if choice == '1':
        api_key = getpass.getpass("Enter your Canalyst API key: ").strip()
        
        if api_key:
            # For Windows
            os.system(f'setx CANALYST_API_KEY "{api_key}"')
            
            print("\n[SUCCESS] API key saved to environment variable!")
            print("\nIMPORTANT: You may need to:")
            print("1. Close and reopen your terminal/command prompt")
            print("2. Or run: set CANALYST_API_KEY=" + api_key[:8] + "...")
            
    elif choice == '2':
        username = input("Enter your Canalyst username: ").strip()
        password = getpass.getpass("Enter your Canalyst password: ").strip()
        
        if username and password:
            # For Windows
            os.system(f'setx CANALYST_USERNAME "{username}"')
            os.system(f'setx CANALYST_PASSWORD "{password}"')
            
            print("\n[SUCCESS] Credentials saved to environment variables!")
            print("\nIMPORTANT: You may need to:")
            print("1. Close and reopen your terminal/command prompt")
            print("2. Or run:")
            print(f"   set CANALYST_USERNAME={username}")
            print("   set CANALYST_PASSWORD=***")
    
    else:
        print("[ERROR] Invalid choice")
        return
    
    print("\nTo test your setup, run:")
    print("   python canalyst_api_solution.py")

if __name__ == "__main__":
    setup_auth()