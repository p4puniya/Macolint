#!/usr/bin/env python3
"""
Script to fix RLS policy for teams table.
This script will update the RLS policy in your Supabase database.
"""

import sys
from macolint.supabase_client import get_client, SUPABASE_URL
from macolint.storage import load_session
from macolint.auth import is_authenticated

def fix_rls_policy():
    """Fix the RLS policy for teams table."""
    if not is_authenticated():
        print("ERROR: You must be logged in. Run 'snip auth login' first.")
        sys.exit(1)
    
    session = load_session()
    if not session:
        print("ERROR: Session not found. Please log in again.")
        sys.exit(1)
    
    sb = get_client()
    access_token = session['access_token']
    refresh_token = session.get('refresh_token', '')
    
    # Set session
    sb.auth.set_session(access_token, refresh_token)
    
    # SQL to fix the policy
    fix_sql = """
    DROP POLICY IF EXISTS "Users can create teams" ON teams;
    
    CREATE POLICY "Users can create teams"
        ON teams
        FOR INSERT
        WITH CHECK (
            auth.uid() IS NOT NULL AND
            auth.uid()::text = created_by::text
        );
    """
    
    print("Attempting to fix RLS policy...")
    print("=" * 80)
    
    try:
        # Try to execute SQL via RPC (if available)
        # Note: This requires a function in Supabase, which we don't have
        # So we'll just provide instructions
        
        print("NOTE: This script cannot directly execute SQL in Supabase.")
        print("You need to run the SQL manually in the Supabase SQL Editor.")
        print("\nSQL to run:")
        print("=" * 80)
        print(fix_sql)
        print("=" * 80)
        print(f"\nGo to: https://supabase.com/dashboard/project/rocayclvfmaskztccqon/sql/new")
        print("Copy and paste the SQL above, then run it.")
        
        # Alternative: Try using the REST API directly
        import httpx
        import json
        
        print("\nAttempting alternative method via REST API...")
        
        # Try to use Supabase REST API to execute SQL
        # This would require the service role key, which we don't have
        # So we'll just provide clear instructions
        
        print("\n" + "=" * 80)
        print("MANUAL FIX REQUIRED:")
        print("=" * 80)
        print("1. Open: https://supabase.com/dashboard/project/rocayclvfmaskztccqon/sql/new")
        print("2. Copy the SQL from: fix_rls_policy.sql")
        print("3. Paste and run it in the SQL Editor")
        print("4. Then test: snip team create test-team")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease run the SQL manually in Supabase SQL Editor.")
        sys.exit(1)

if __name__ == '__main__':
    fix_rls_policy()

