"""Team management operations for Macolint."""

from typing import Optional, List
from rich.console import Console

from macolint.supabase_client import get_authenticated_client, ensure_auth_headers
from macolint.storage import load_session
from macolint.auth import is_authenticated, get_access_token
from macolint.models import Team, TeamMember

console = Console()


def create_team(name: str) -> Optional[Team]:
    """
    Create a new team.
    
    Args:
        name: Team name (must be unique)
    
    Returns:
        Team object if successful, None otherwise
    
    Raises:
        RuntimeError: If not authenticated or team creation fails
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    
    # WORKAROUND: Use direct HTTP request instead of Python client
    # The Python client has issues with RLS policies for INSERT operations
    # Direct HTTP requests work correctly
    from macolint.supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY
    import httpx
    import json
    
    access_token = session.get("access_token")
    url = f"{SUPABASE_URL}/rest/v1/teams"
    # Use minimal headers - same as working direct HTTP test
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "name": name,
        "created_by": user_id  # Explicitly set, but DEFAULT auth.uid() will also work
    }
    
    try:
        with httpx.Client() as http_client:
            response = http_client.post(url, headers=headers, json=data)
            if response.status_code == 201:
                # Success - response is usually empty, so fetch the team by name
                # Small delay to ensure the database has committed
                import time
                time.sleep(0.1)
                
                # Fetch the created team
                team = get_team_by_name(name)
                if not team:
                    raise RuntimeError("Team created but could not retrieve it. Please try again.")
            else:
                # Error
                try:
                    error_data = response.json() if response.text else {}
                except Exception:
                    error_data = {"message": response.text or "Unknown error", "status_code": response.status_code}
                raise RuntimeError(f"Failed to create team: {error_data}")
        
        # Automatically add creator as team member
        # Note: A database trigger should also do this automatically, but we do it here
        # as a safety measure in case the trigger fails or hasn't been set up
        try:
            # Use direct HTTP for team_members insert too
            members_url = f"{SUPABASE_URL}/rest/v1/team_members"
            members_data = {
                "team_id": team.id,
                "user_id": user_id,
                "role": "owner"
            }
            
            with httpx.Client() as http_client:
                members_response = http_client.post(members_url, headers=headers, json=members_data)
                if members_response.status_code not in (201, 204):
                    # If it fails, it might be because trigger already added it
                    pass
        except Exception as e:
            # If adding member fails, the trigger might have already added it
            # or there might be a duplicate - check if it's a unique constraint error
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                # Trigger probably already added the member, which is fine
                pass
            else:
                # Some other error - log it but don't fail
                console.print(f"[yellow]Warning: Team created but failed to add you as member: {e}[/yellow]")
        
        return team
    except Exception as e:
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise RuntimeError(f"Team '{name}' already exists.")
        raise RuntimeError(f"Failed to create team: {e}")


def list_user_teams() -> List[Team]:
    """
    List all teams the current user is a member of.
    
    Returns:
        List of Team objects
    
    Raises:
        RuntimeError: If not authenticated
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    
    # Get authenticated client (ensures JWT is properly set)
    sb = get_authenticated_client()
    
    try:
        # Get teams where user is a member
        response = sb.table("team_members").select("team_id, teams(*)").eq("user_id", user_id).execute()
        
        teams = []
        if response.data:
            for member_data in response.data:
                if "teams" in member_data and member_data["teams"]:
                    team_data = member_data["teams"]
                    teams.append(Team.from_dict(team_data))
        
        return teams
    except Exception as e:
        raise RuntimeError(f"Failed to list teams: {e}")


def get_team_by_name(name: str) -> Optional[Team]:
    """
    Get a team by name.
    
    Args:
        name: Team name
    
    Returns:
        Team object if found and user is a member, None otherwise
    
    Raises:
        RuntimeError: If not authenticated
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    
    # Get authenticated client (ensures JWT is properly set)
    sb = get_authenticated_client()
    
    try:
        # Get team by name, but only if user is a member
        response = sb.table("teams").select("*").eq("name", name).execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        team = Team.from_dict(response.data[0])
        
        # Verify user is a member
        if not is_user_in_team(team.id, user_id):
            return None
        
        return team
    except Exception as e:
        raise RuntimeError(f"Failed to get team: {e}")


def get_user_id_by_email(user_email: str) -> Optional[str]:
    """
    Get user ID (UUID) by email address.
    
    This function queries Supabase auth.users table to find the user ID.
    Uses a database function if available, otherwise provides helpful error.
    
    Args:
        user_email: Email address of the user
    
    Returns:
        User ID (UUID) if found, None otherwise
    
    Raises:
        RuntimeError: If not authenticated or lookup fails
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    # Get authenticated client
    sb = get_authenticated_client()
    
    # Normalize email (lowercase, trim)
    normalized_email = user_email.lower().strip()
    
    # Try to look up user by email using database function
    try:
        # Call the database function to get user ID by email
        # PostgREST expects the parameter name to match exactly
        response = sb.rpc('get_user_id_by_email', {'user_email': normalized_email}).execute()
        
        # Supabase RPC functions that return a single value return it directly
        # But sometimes it's wrapped in a list or dict, so handle both cases
        user_id = response.data
        
        # Handle different response formats
        if user_id is None:
            raise RuntimeError(
                f"User with email '{user_email}' not found. "
                "They must register an account first using 'snip auth signup'."
            )
        
        # If it's a list, get the first element
        if isinstance(user_id, list):
            user_id = user_id[0] if len(user_id) > 0 else None
        
        # If it's a dict, try to get the value
        if isinstance(user_id, dict):
            user_id = user_id.get('get_user_id_by_email') or user_id.get('id') or user_id.get('user_id')
        
        if not user_id:
            raise RuntimeError(
                f"User with email '{user_email}' not found. "
                "They must register an account first using 'snip auth signup'."
            )
        
        return str(user_id)
    except RuntimeError:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if it's a function not found error
        if "PGRST202" in error_msg or "Could not find the function" in error_msg or "schema cache" in error_msg.lower():
            # Provide clear instructions
            console.print("\n[red]Error: Database function not found.[/red]")
            console.print("\n[yellow]To fix this, run the following SQL in your Supabase SQL Editor:[/yellow]")
            console.print("\n[cyan]1. Open Supabase Dashboard → SQL Editor[/cyan]")
            console.print("[cyan]2. Copy and paste the contents of: get_user_by_email_function.sql[/cyan]")
            console.print("[cyan]3. Click 'Run' to execute the SQL[/cyan]")
            console.print("\n[dim]This will create the function needed to look up users by email.[/dim]\n")
            raise RuntimeError(
                "Database function 'get_user_id_by_email' not found. "
                "Please run 'get_user_by_email_function.sql' in your Supabase SQL Editor. "
                "See instructions above."
            )
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            raise RuntimeError(
                f"User with email '{user_email}' not found. "
                "They must register an account first using 'snip auth signup'."
            )
        raise RuntimeError(f"Failed to look up user by email: {e}")


def add_team_member(team_id: str, user_email: str) -> bool:
    """
    Add a user to a team by email address.
    
    Args:
        team_id: Team ID
        user_email: Email address of the user to add
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        RuntimeError: If not authenticated, user not found, or operation fails
    """
    # Get user ID from email
    user_id = get_user_id_by_email(user_email)
    if not user_id:
        raise RuntimeError(f"User with email '{user_email}' not found. They must register first.")
    
    # Use the existing add_team_member_by_id function
    return add_team_member_by_id(team_id, user_id)


def add_team_member_by_id(team_id: str, user_id: str) -> bool:
    """
    Add a user to a team by user ID.
    
    Args:
        team_id: Team ID
        user_id: User ID to add
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        RuntimeError: If not authenticated or operation fails
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    current_user_id = session["user"]["id"]
    
    # Get authenticated client (ensures JWT is properly set)
    sb = get_authenticated_client()
    
    # Verify current user is team creator
    try:
        team_response = sb.table("teams").select("created_by").eq("id", team_id).execute()
        if not team_response.data or team_response.data[0]["created_by"] != current_user_id:
            raise RuntimeError("Only team creators can add members.")
    except Exception as e:
        raise RuntimeError(f"Failed to verify team access: {e}")
    
    try:
        # Check if member already exists
        existing = sb.table("team_members").select("id").eq("team_id", team_id).eq("user_id", user_id).execute()
        if existing.data and len(existing.data) > 0:
            raise RuntimeError("User is already a member of this team.")
        
        # Add member
        response = sb.table("team_members").insert({
            "team_id": team_id,
            "user_id": user_id,
            "role": "member"
        }).execute()
        
        return response.data is not None and len(response.data) > 0
    except Exception as e:
        error_msg = str(e).lower()
        if "already" in error_msg or "unique" in error_msg:
            raise RuntimeError("User is already a member of this team.")
        raise RuntimeError(f"Failed to add team member: {e}")


def list_team_members(team_id: str) -> List[TeamMember]:
    """
    List all members of a team.
    
    Args:
        team_id: Team ID
    
    Returns:
        List of TeamMember objects
    
    Raises:
        RuntimeError: If not authenticated or user is not a team member
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    
    # Verify user is a team member
    if not is_user_in_team(team_id, user_id):
        raise RuntimeError("You are not a member of this team.")
    
    # Get authenticated client (ensures JWT is properly set)
    sb = get_authenticated_client()
    
    try:
        response = sb.table("team_members").select("*").eq("team_id", team_id).execute()
        
        members = []
        if response.data:
            for member_data in response.data:
                members.append(TeamMember.from_dict(member_data))
        
        return members
    except Exception as e:
        raise RuntimeError(f"Failed to list team members: {e}")


def is_user_in_team(team_id: str, user_id: str) -> bool:
    """
    Check if a user is a member of a team.
    
    Args:
        team_id: Team ID
        user_id: User ID
    
    Returns:
        True if user is a member, False otherwise
    
    Raises:
        RuntimeError: If not authenticated
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    # Get authenticated client (ensures JWT is properly set)
    sb = get_authenticated_client()
    
    try:
        response = sb.table("team_members").select("id").eq("team_id", team_id).eq("user_id", user_id).execute()
        return response.data is not None and len(response.data) > 0
    except Exception:
        return False

