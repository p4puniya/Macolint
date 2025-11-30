"""Supabase client initialization and configuration.

SETUP INSTRUCTIONS FOR MACOLINT MAINTAINERS:
============================================

To enable cloud sync for all Macolint users:

1. Create a Supabase project at https://app.supabase.com
2. Set up the database schema (see README.md for SQL)
3. Enable Row-Level Security (RLS) on all tables
4. Get your project URL and anon key from Project Settings → API
5. Set the values below:

   DEFAULT_SUPABASE_URL = "https://yourproject.supabase.co"
   DEFAULT_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

SECURITY NOTE:
=============
The Supabase anon key is designed to be public and safe to include in client applications.
Security is enforced by Row-Level Security (RLS) policies that ensure users can only
access their own data. Each user's snippets are also encrypted with their own passphrase
before being uploaded, providing end-to-end encryption.

USER OVERRIDE:
=============
Users can override these defaults by setting SUPABASE_URL and SUPABASE_ANON_KEY in
their .env file or environment variables if they want to use their own Supabase instance.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Default Supabase credentials (for shared Macolint cloud sync)
# Set these to enable cloud sync for all users (for maintainers only)
DEFAULT_SUPABASE_URL: Optional[str] = "https://rocayclvfmaskztccqon.supabase.co" # Set this to your Supabase project URL
DEFAULT_SUPABASE_ANON_KEY: Optional[str] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJvY2F5Y2x2Zm1hc2t6dGNjcW9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0ODU5ODAsImV4cCI6MjA4MDA2MTk4MH0.SHnVoP91AQCoJjgCGIs1fQNwZ4pP6tYnrA1qjgAAMPc" # Set this to your Supabase anon key

# Load environment variables from .env file (allows users to override defaults)
load_dotenv()

# Use environment variables if set, otherwise fall back to defaults
SUPABASE_URL = os.environ.get("SUPABASE_URL") or DEFAULT_SUPABASE_URL
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or DEFAULT_SUPABASE_ANON_KEY

# Initialize Supabase client
sb: Optional[Client] = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        # Client creation failed, but we'll handle this gracefully in auth/sync modules
        sb = None
else:
    # Environment variables not set - will be handled when auth/sync is attempted
    sb = None


def get_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Supabase client instance
    
    Raises:
        RuntimeError: If Supabase is not configured (missing credentials)
    """
    if sb is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(
                "Supabase is not configured. The Macolint cloud sync service is not set up.\n"
                "Please contact the Macolint maintainer or set up your own Supabase instance:\n"
                "  - Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file, or\n"
                "  - Set them as environment variables"
            )
        raise RuntimeError("Failed to initialize Supabase client.")
    return sb


def is_configured() -> bool:
    """
    Check if Supabase is configured.
    
    Returns:
        True if both URL and key are set, False otherwise
    """
    return SUPABASE_URL is not None and SUPABASE_ANON_KEY is not None

