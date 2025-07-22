"""Quick API key setup - for when you can't use hidden input"""

import os

print("Quick API Key Setup")
print("=" * 50)
print("\nPaste your Canalyst API token below and press Enter:")
api_key = input("API Token: ").strip()

if api_key:
    with open(".env", "w") as f:
        f.write(f"CANALYST_API_TOKEN={api_key}\n")
    print("\nAPI key saved to .env file!")
    print("You can now run the app.")
else:
    print("\nNo API key provided.")