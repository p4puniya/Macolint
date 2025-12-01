#!/usr/bin/env python3
"""
Script to create the get_user_id_by_email function in Supabase.
Run this after logging in to automatically create the required function.
"""

from macolint.supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY, get_authenticated_client
from macolint.auth import is_authenticated
from macolint.storage import load_session
import httpx

def create_function():
    """Create the get_user_id_by_email function in Supabase."""
    
    if not is_authenticated():
        print("Error: Not logged in. Run 'snip auth login' first.")
        return False
    
    session = load_session()
    if not session:
        print("Error: Session not found. Please log in again.")
        return False
    
    access_token = session.get("access_token")
    
    # Read the SQL function
    sql_file = "get_user_by_email_function.sql"
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
    except FileNotFoundError:
        print(f"Error: {sql_file} not found.")
        return False
    
    # Execute SQL using Supabase REST API
    # Note: This requires the SQL to be executed via the Supabase API
    # We'll use the PostgREST endpoint for executing SQL
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Actually, Supabase doesn't have a direct SQL execution endpoint
    # We need to use the Management API or run it manually
    print("Note: Supabase doesn't allow executing arbitrary SQL via the client API.")
    print("You need to run the SQL manually in the Supabase Dashboard.")
    print(f"\nSQL to run is in: {sql_file}")
    print("\nSteps:")
    print("1. Go to https://app.supabase.com")
    print("2. Select your project")
    print("3. Go to SQL Editor")
    print("4. Copy and paste the contents of get_user_by_email_function.sql")
    print("5. Click 'Run'")
    
    return False

if __name__ == "__main__":
    create_function()

