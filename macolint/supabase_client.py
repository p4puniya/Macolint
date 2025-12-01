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
# Try multiple locations: project root, ~/.macolint/, and current directory
from pathlib import Path
env_paths = [
    Path.cwd() / ".env",
    Path.home() / ".macolint" / ".env",
    Path(__file__).parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        try:
            load_dotenv(env_path, override=False)
            break
        except Exception as e:
            # If .env file has parsing errors, log warning but continue
            # This allows the app to work even with malformed .env files
            import warnings
            warnings.warn(f"Could not parse .env file at {env_path}: {e}. Using defaults.", UserWarning)
            pass

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


def get_authenticated_client() -> Client:
    """
    Get an authenticated Supabase client with JWT token properly set.
    
    This function ensures that:
    1. The user is authenticated (has a valid session)
    2. The session is set on the Supabase client
    3. The Authorization header is manually set on the PostgREST client
       (because set_session() doesn't always propagate JWT to PostgREST)
    
    Returns:
        Authenticated Supabase client instance
    
    Raises:
        RuntimeError: If not authenticated or session is invalid
    """
    from macolint.storage import load_session
    from macolint.auth import is_authenticated
    
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token", "")
    
    if not access_token:
        raise RuntimeError("No access token found in session. Please log in again.")
    
    # CRITICAL: Create a NEW client instance for each authenticated request
    # Reusing the shared client can cause session state issues
    # Creating a fresh client ensures the session is properly initialized
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    # Set session on auth client
    # The Supabase Python client's set_session() method signature:
    # set_session(access_token: str, refresh_token: str) -> AuthResponse
    try:
        auth_response = client.auth.set_session(access_token, refresh_token)
        # Verify the session was set correctly by getting the current user
        # This ensures the token is valid and the session is active
        try:
            user_response = client.auth.get_user()
            if not user_response or not user_response.user:
                raise RuntimeError("Session is invalid. Please log in again.")
        except Exception as e:
            # If get_user fails, the session might still be valid for RLS
            # But log a warning
            import warnings
            warnings.warn(f"Could not verify session with get_user(): {e}. Continuing anyway.")
    except Exception as e:
        raise RuntimeError(f"Failed to set session: {e}. Please log in again with 'snip auth login'.")
    
    # CRITICAL FIX: Manually set Authorization header on PostgREST client
    # The Supabase Python client's set_session() doesn't always properly
    # sync the JWT token to PostgREST client for INSERT/UPDATE/DELETE operations
    # This ensures the JWT is always included in database requests
    
    # CRITICAL FIX: Manually set Authorization header on PostgREST client
    # The Supabase Python client's set_session() doesn't always properly
    # sync the JWT token to PostgREST client for INSERT/UPDATE/DELETE operations
    # This ensures the JWT is always included in database requests
    
    # Set headers on the postgrest session (httpx.Client)
    # This is the most reliable way to ensure headers are sent with requests
    if hasattr(client, 'postgrest'):
        # Set on the httpx.Client session - this is the actual HTTP client that makes requests
        if hasattr(client.postgrest, 'session') and hasattr(client.postgrest.session, 'headers'):
            # Use lowercase 'authorization' as httpx normalizes headers
            client.postgrest.session.headers['authorization'] = f'Bearer {access_token}'
            client.postgrest.session.headers['Authorization'] = f'Bearer {access_token}'  # Also set uppercase for compatibility
            client.postgrest.session.headers['apikey'] = SUPABASE_ANON_KEY
        
        # Also set on postgrest client's headers (if it exists)
        if hasattr(client.postgrest, 'headers'):
            client.postgrest.headers['authorization'] = f'Bearer {access_token}'
            client.postgrest.headers['Authorization'] = f'Bearer {access_token}'  # Also set uppercase
            client.postgrest.headers['apikey'] = SUPABASE_ANON_KEY
    
    # Store access_token for debugging/verification
    client._macolint_access_token = access_token
    
    return client


def ensure_auth_headers(client: Client) -> None:
    """
    Ensure Authorization headers are set on the client right before a request.
    
    This should be called right before making database operations to ensure
    the JWT token is included in the request headers.
    
    Args:
        client: Supabase client instance
    """
    from macolint.storage import load_session
    
    session = load_session()
    if not session:
        return
    
    access_token = session.get("access_token")
    if not access_token:
        return
    
    # Set headers on the postgrest session (httpx.Client)
    if hasattr(client, 'postgrest'):
        # Set on the httpx.Client session - this is the actual HTTP client that makes requests
        if hasattr(client.postgrest, 'session') and hasattr(client.postgrest.session, 'headers'):
            # Use lowercase 'authorization' as httpx normalizes headers
            client.postgrest.session.headers['authorization'] = f'Bearer {access_token}'
            client.postgrest.session.headers['Authorization'] = f'Bearer {access_token}'  # Also set uppercase for compatibility
            client.postgrest.session.headers['apikey'] = SUPABASE_ANON_KEY
        
        # Also set on postgrest client's headers (if it exists)
        if hasattr(client.postgrest, 'headers'):
            client.postgrest.headers['authorization'] = f'Bearer {access_token}'
            client.postgrest.headers['Authorization'] = f'Bearer {access_token}'  # Also set uppercase
            client.postgrest.headers['apikey'] = SUPABASE_ANON_KEY

