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
    
    # Use Supabase's PKCE flow for email authentication.
    # For now we only expose the Email/Password flow in the UI.
    # The Magic Link flow is kept below but not offered to users yet.
    console.print(
        Panel(
            "[bold]Authentication[/bold]\n\n"
            "[yellow]Email/Password login[/yellow]\n"
            "1. Enter your email and password below\n"
            "2. We will authenticate with Supabase and store your session locally\n\n"
            "[dim]Note: Magic link login exists in the codebase but is currently disabled in the UI.[/dim]",
            title="Authentication",
            border_style="cyan",
        )
    )
    
    # For now we only allow email/password (method \"2\").
    # Previous prompt for magic link vs password is kept for later:
    # method = console.input(\"\\n[bold cyan]Choose method (1 for Magic Link, 2 for Email/Password) [1]: [/bold cyan]\").strip() or \"1\"
    method = "2"
    
    if method == "1":
        # Magic Link flow
        email = console.input("\n[bold cyan]Enter your email: [/bold cyan]").strip()
        if not email:
            console.print("[red]Email is required.[/red]")
            return False
        
        try:
            # Send magic link with timeout handling
            # Use a simple redirect URL that will show the token in the URL fragment
            # The redirect should point to a page that can display the token
            redirect_url = f"{SUPABASE_URL}/auth/v1/callback"
            response = sb.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "email_redirect_to": redirect_url
                }
            })
            
            console.print(f"\n[green]✓ Magic link sent to {email}[/green]")
            console.print("[yellow]Please check your email and click the magic link.[/yellow]")
            console.print("\n[bold]After clicking the link:[/bold]")
            console.print("1. You'll be redirected to a page")
            console.print("2. Look for 'access_token' in the URL (after #access_token=)")
            console.print("3. Copy the entire token and paste it below")
            console.print("\n[yellow]Note: If you don't receive the email, check your spam folder.[/yellow]")
            console.print("[yellow]You may need to configure SMTP in your Supabase project settings.[/yellow]")
            
            token = console.input("\n[bold cyan]Paste your access token: [/bold cyan]").strip()
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                console.print(f"\n[yellow]Magic link request timed out. This usually means:[/yellow]")
                console.print("[yellow]1. SMTP is not configured in your Supabase project[/yellow]")
                console.print("[yellow]2. Network connectivity issues[/yellow]")
                console.print("\n[yellow]Switching to email/password method...[/yellow]\n")
            else:
                console.print(f"[red]Error sending magic link: {e}[/red]")
                console.print("[yellow]Switching to email/password method...[/yellow]\n")
            method = "2"
    
    if method == "2":
        # Email/Password flow
        email = console.input("\n[bold cyan]Enter your email: [/bold cyan]").strip()
        if not email:
            console.print("[red]Email is required.[/red]")
            return False
        
        import getpass
        console.print("[bold cyan]Enter your password: [/bold cyan]", end="")
        password = getpass.getpass("")
        if not password:
            console.print("[red]Password is required.[/red]")
            return False
        
        try:
            # Try to sign in first
            try:
                response = sb.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
            except Exception as sign_in_error:
                # If sign in fails, try to sign up (user might not exist)
                error_msg = str(sign_in_error).lower()
                if "invalid" in error_msg or "credentials" in error_msg or "user not found" in error_msg:
                    console.print("[yellow]Account not found. Attempting to create account...[/yellow]")
                    try:
                        response = sb.auth.sign_up({
                            "email": email,
                            "password": password
                        })
                        # Check if user was created (even if session is None due to email confirmation)
                        if response and response.user:
                            if response.session:
                                # Email confirmation not required, user is logged in
                                token = response.session.access_token
                                refresh_token = getattr(response.session, 'refresh_token', None) or ""
                                user = response.user
                                
                                session_data = {
                                    "access_token": token,
                                    "refresh_token": refresh_token,
                                    "user": {
                                        "id": user.id,
                                        "email": user.email,
                                    }
                                }
                                save_session(session_data)
                                
                                console.print(f"[green]✓ Account created and logged in as {user.email}[/green]")
                                return True
                            else:
                                # Account created but email confirmation required
                                console.print(f"[green]✓ Account created successfully for {response.user.email}[/green]")
                                console.print("\n[yellow]Email confirmation required:[/yellow]")
                                console.print("1. Check your email for a confirmation link")
                                console.print("2. Click the link to confirm your account")
                                console.print("3. Then run 'snip auth login' again and sign in with your email/password")
                                console.print("\n[dim]Note: The confirmation link may expire. If it does, try signing in - Supabase may auto-confirm on first login.[/dim]")
                                return False
                        else:
                            console.print("[red]Failed to create account. No user data returned.[/red]")
                            return False
                    except Exception as sign_up_error:
                        error_msg = str(sign_up_error).lower()
                        # Check if the error is actually about email sending, or if account was created anyway
                        if "confirmation email" in error_msg or "smtp" in error_msg:
                            # Even if email sending failed, the account might have been created
                            # Try to check if we can sign in (some Supabase configs auto-confirm)
                            console.print(f"\n[yellow]Email sending failed, but account may have been created.[/yellow]")
                            console.print("[yellow]Attempting to sign in (some configurations auto-confirm accounts)...[/yellow]")
                            try:
                                # Try signing in - if account exists and is confirmed, this will work
                                sign_in_response = sb.auth.sign_in_with_password({
                                    "email": email,
                                    "password": password
                                })
                                if sign_in_response and sign_in_response.session:
                                    token = sign_in_response.session.access_token
                                    refresh_token = getattr(sign_in_response.session, 'refresh_token', None) or ""
                                    user = sign_in_response.user
                                    
                                    session_data = {
                                        "access_token": token,
                                        "refresh_token": refresh_token,
                                        "user": {
                                            "id": user.id,
                                            "email": user.email,
                                        }
                                    }
                                    save_session(session_data)
                                    
                                    console.print(f"[green]✓ Successfully logged in as {user.email}[/green]")
                                    console.print("[yellow]Note: Your account was created. Check your email for confirmation if needed.[/yellow]")
                                    return True
                            except:
                                pass
                            
                            # If sign-in didn't work, provide instructions
                            console.print(f"\n[red]Account creation had issues with email confirmation.[/red]")
                            console.print("\n[yellow]To fix this, you have two options:[/yellow]")
                            console.print("\n[bold]Option 1: Configure SMTP in Supabase (Recommended)[/bold]")
                            console.print("1. Go to your Supabase dashboard")
                            console.print("2. Navigate to Authentication → Settings → SMTP Settings")
                            console.print("3. Configure your SMTP provider (Gmail, SendGrid, etc.)")
                            console.print("4. Try signing up again\n")
                            console.print("[bold]Option 2: Disable email confirmation (Testing only)[/bold]")
                            console.print("1. Go to Supabase dashboard → Authentication → Providers → Email")
                            console.print("2. Disable 'Confirm email' toggle")
                            console.print("3. Try signing up again\n")
                            console.print("[yellow]Note: Disabling email confirmation reduces security. Use only for testing.[/yellow]")
                        else:
                            console.print(f"[red]Failed to create account: {sign_up_error}[/red]")
                        return False
                else:
                    raise sign_in_error
            
            if response and response.session and response.session.access_token:
                token = response.session.access_token
                refresh_token = getattr(response.session, 'refresh_token', None) or ""
                user = response.user
                
                # Save session
                session_data = {
                    "access_token": token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                    }
                }
                save_session(session_data)
                
                console.print(f"\n[green]✓ Successfully logged in as {user.email}[/green]")
                return True
            else:
                console.print("[red]Authentication failed. Invalid credentials.[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Authentication failed: {e}[/red]")
            return False
    
    # If we got here from magic link flow, validate the token
    if 'token' in locals() and token:
        # Validate token by trying to get user info
        try:
            # Set the session with the token
            # Use empty string for refresh_token if not available (Supabase requires string, not None)
            sb.auth.set_session(token, "")
            
            # Get user info to validate token
            user_response = sb.auth.get_user(token)
            if not user_response or not user_response.user:
                console.print("[red]Invalid token. Please try again.[/red]")
                return False
            
            user = user_response.user
            
            # Save session
            session_data = {
                "access_token": token,
                "refresh_token": "",  # Magic link doesn't provide refresh token
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
    
    return False


def signup() -> bool:
    """
    Create a new account for cloud sync.
    
    Prompts for email and password, creates account, and optionally logs in.
    
    Returns:
        True if signup successful, False otherwise
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
    
    console.print(
        Panel(
            "[bold]Create a new account for Macolint cloud sync[/bold]\n\n"
            "You'll need:\n"
            "- A valid email address\n"
            "- A secure password\n\n"
            "[dim]After signing up, you may need to confirm your email depending on your Supabase configuration.[/dim]",
            title="Sign Up",
            border_style="cyan"
        )
    )
    
    # Get email
    email = console.input("\n[bold cyan]Enter your email: [/bold cyan]").strip()
    if not email:
        console.print("[red]Email is required.[/red]")
        return False
    
    # Get password
    import getpass
    console.print("[bold cyan]Enter your password: [/bold cyan]", end="")
    password = getpass.getpass("")
    if not password:
        console.print("[red]Password is required.[/red]")
        return False
    
    # Confirm password
    console.print("[bold cyan]Confirm your password: [/bold cyan]", end="")
    password_confirm = getpass.getpass("")
    if password != password_confirm:
        console.print("[red]Passwords do not match.[/red]")
        return False
    
    try:
        # Sign up
        response = sb.auth.sign_up({
            "email": email,
            "password": password
        })
        
        # Check if user was created (even if session is None due to email confirmation)
        if response and response.user:
            if response.session:
                # Email confirmation not required, user is logged in
                token = response.session.access_token
                refresh_token = getattr(response.session, 'refresh_token', None) or ""
                user = response.user
                
                session_data = {
                    "access_token": token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                    }
                }
                save_session(session_data)
                
                console.print(f"\n[green]✓ Account created and logged in as {user.email}[/green]")
                console.print("[yellow]You can now use 'snip sync push' to upload your snippets.[/yellow]")
                return True
            else:
                # Account created but email confirmation required
                console.print(f"\n[green]✓ Account created successfully for {response.user.email}[/green]")
                console.print("\n[yellow]Email confirmation required:[/yellow]")
                console.print("1. Check your email for a confirmation link")
                console.print("2. Click the link to confirm your account")
                console.print("3. Then run 'snip auth login' to sign in")
                console.print("\n[dim]Note: The confirmation link may expire. If it does, try signing in - Supabase may auto-confirm on first login.[/dim]")
                return False
        else:
            console.print("[red]Failed to create account. No user data returned.[/red]")
            return False
            
    except Exception as sign_up_error:
        error_msg = str(sign_up_error).lower()
        # Check if the error is actually about email sending, or if account was created anyway
        if "confirmation email" in error_msg or "smtp" in error_msg:
            # Even if email sending failed, the account might have been created
            # Try to check if we can sign in (some Supabase configs auto-confirm)
            console.print(f"\n[yellow]Email sending failed, but account may have been created.[/yellow]")
            console.print("[yellow]Attempting to sign in (some configurations auto-confirm accounts)...[/yellow]")
            try:
                # Try signing in - if account exists and is confirmed, this will work
                sign_in_response = sb.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                if sign_in_response and sign_in_response.session:
                    token = sign_in_response.session.access_token
                    refresh_token = getattr(sign_in_response.session, 'refresh_token', None) or ""
                    user = sign_in_response.user
                    
                    session_data = {
                        "access_token": token,
                        "refresh_token": refresh_token,
                        "user": {
                            "id": user.id,
                            "email": user.email,
                        }
                    }
                    save_session(session_data)
                    
                    console.print(f"[green]✓ Successfully logged in as {user.email}[/green]")
                    console.print("[yellow]Note: Your account was created. Check your email for confirmation if needed.[/yellow]")
                    return True
            except:
                pass
            
            # If sign-in didn't work, provide instructions
            console.print(f"\n[red]Account creation had issues with email confirmation.[/red]")
            console.print("\n[yellow]To fix this, you have two options:[/yellow]")
            console.print("\n[bold]Option 1: Configure SMTP in Supabase (Recommended)[/bold]")
            console.print("1. Go to your Supabase dashboard")
            console.print("2. Navigate to Authentication → Settings → SMTP Settings")
            console.print("3. Configure your SMTP provider (Gmail, SendGrid, etc.)")
            console.print("4. Try signing up again\n")
            console.print("[bold]Option 2: Disable email confirmation (Testing only)[/bold]")
            console.print("1. Go to Supabase dashboard → Authentication → Providers → Email")
            console.print("2. Disable 'Confirm email' toggle")
            console.print("3. Try signing up again\n")
            console.print("[yellow]Note: Disabling email confirmation reduces security. Use only for testing.[/yellow]")
        else:
            # Check if user already exists
            if "already registered" in error_msg or "user already exists" in error_msg:
                console.print(f"[red]An account with this email already exists.[/red]")
                console.print("[yellow]Use 'snip auth login' to sign in instead.[/yellow]")
            else:
                console.print(f"[red]Failed to create account: {sign_up_error}[/red]")
        return False


def logout(clear_team_snippets: bool = True) -> bool:
    """
    Log out the current user by clearing the session.
    
    Args:
        clear_team_snippets: If True, removes all team-shared snippets from local database.
                           This is recommended for security/privacy when logging out.
    
    Returns:
        True if logout successful, False otherwise
    """
    session = load_session()
    if not session:
        console.print("[yellow]No active session found.[/yellow]")
        return False
    
    # Clear team-shared snippets if requested
    if clear_team_snippets:
        from macolint.database import Database
        db = Database()
        shared_snippets = db.get_shared_snippets()
        
        if shared_snippets:
            removed_count = 0
            for snippet_path in shared_snippets:
                try:
                    if db.delete_snippet(snippet_path):
                        removed_count += 1
                except Exception:
                    # If deletion fails, continue with others
                    pass
            
            if removed_count > 0:
                console.print(f"[yellow]Removed {removed_count} team-shared snippet(s) from local database.[/yellow]")
    
    delete_session()
    console.print("[green]✓ Successfully logged out[/green]")
    if clear_team_snippets:
        console.print("[dim]Team-shared snippets have been removed. You can pull them again after logging back in.[/dim]")
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

