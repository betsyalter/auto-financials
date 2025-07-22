import os
from dotenv import load_dotenv

load_dotenv()

def get_api_token(user_provided_token=None):
    """Get API token from various sources in order of preference"""
    
    # 1. User-provided token (from UI)
    if user_provided_token and user_provided_token.strip():
        return user_provided_token.strip()
    
    # 2. Environment variable
    token = os.getenv('CANALYST_API_TOKEN')
    if token:
        return token
    
    # 3. Streamlit secrets
    try:
        import streamlit as st
        token = st.secrets.get("CANALYST_API_TOKEN")
        if token:
            return token
    except:
        pass
    
    return None