"""Authentication functions for Supabase."""

import webbrowser
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel

from macolint.supabase_client import get_client, is_configured, SUPABASE_URL
from macolint.storage import save_session, load_session, delete_session

console = Console()


def login() -> bool:
    """
    Authenticate user using manual token-paste flow.
    
    Opens browser to Supabase auth page, instructs user to copy access token,
    then prompts for token in CLI and validates it.
    
    Returns:
        True if login successful, False otherwise
    """
    if not is_configured():
        console.print(
            "[red]Error: Supabase is not configured.[/red]\n"
            "[yellow]Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file.[/yellow]"
        )
        return False
    
    try:
        sb = get_client()
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
    
    # Construct auth URL - redirect to a simple page that shows the token
    # For MVP, we'll use a redirect URI that shows instructions
    redirect_uri = f"{SUPABASE_URL}/auth/v1/callback"
    auth_url = f"{SUPABASE_URL}/auth/v1/authorize?redirect_to={redirect_uri}"
    
    console.print("\n[cyan]Opening browser for authentication...[/cyan]")
    console.print(f"[yellow]If browser doesn't open, visit:[/yellow] {auth_url}\n")
    
    try:
        webbrowser.open(auth_url)
    except Exception:
        console.print(f"[yellow]Could not open browser automatically.[/yellow]")
        console.print(f"[yellow]Please visit:[/yellow] {auth_url}\n")
    
    console.print(
        Panel(
            "[bold]Instructions:[/bold]\n\n"
            "1. Sign in with your email in the browser\n"
            "2. After signing in, you'll be redirected to a page\n"
            "3. Look for the 'access_token' in the URL (after #access_token=)\n"
            "4. Copy the entire access token\n"
            "5. Paste it below when prompted\n\n"
            "[dim]Tip: The token is a long string starting with 'eyJ'[/dim]",
            title="Authentication",
            border_style="cyan"
        )
    )
    
    # Prompt for token
    token = console.input("\n[bold cyan]Paste your access token: [/bold cyan]").strip()
    
    if not token:
        console.print("[red]No token provided. Login cancelled.[/red]")
        return False
    
    # Validate token by trying to get user info
    try:
        # Set the session with the token
        sb.auth.set_session(token, None)  # refresh_token not needed for MVP
        
        # Get user info to validate token
        user_response = sb.auth.get_user(token)
        if not user_response or not user_response.user:
            console.print("[red]Invalid token. Please try again.[/red]")
            return False
        
        user = user_response.user
        
        # Save session
        session_data = {
            "access_token": token,
            "user": {
                "id": user.id,
                "email": user.email,
            }
        }
        save_session(session_data)
        
        console.print(f"\n[green]✓ Successfully logged in as {user.email}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        console.print("[yellow]Please check your token and try again.[/yellow]")
        return False


def logout() -> bool:
    """
    Log out the current user by clearing the session.
    
    Returns:
        True if logout successful, False otherwise
    """
    session = load_session()
    if not session:
        console.print("[yellow]No active session found.[/yellow]")
        return False
    
    delete_session()
    console.print("[green]✓ Successfully logged out[/green]")
    return True


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from session.
    
    Returns:
        User dictionary with 'id' and 'email' if authenticated, None otherwise
    """
    session = load_session()
    if not session:
        return None
    
    return session.get("user")


def is_authenticated() -> bool:
    """
    Check if user is currently authenticated.
    
    Returns:
        True if valid session exists, False otherwise
    """
    session = load_session()
    if not session:
        return False
    
    # Basic validation - check if required fields exist
    if not session.get("access_token") or not session.get("user"):
        return False
    
    # Optionally validate token with Supabase (for MVP, we'll do basic check)
    # For production, you might want to verify token hasn't expired
    return True


def get_access_token() -> Optional[str]:
    """
    Get the current access token from session.
    
    Returns:
        Access token string if authenticated, None otherwise
    """
    session = load_session()
    if not session:
        return None
    
    return session.get("access_token")

