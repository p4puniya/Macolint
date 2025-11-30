"""Sync functions for pushing and pulling snippets to/from Supabase."""

from typing import List, Tuple, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from macolint.supabase_client import get_client
from macolint.crypto import derive_key, encrypt, decrypt, gen_salt, b64, ub64
from macolint.storage import load_session
from macolint.database import Database
from macolint.auth import get_access_token, is_authenticated

console = Console()
db = Database()


def ensure_user_salt(user_id: str, session_token: str) -> bytes:
    """
    Get or create user's salt in users_meta table.
    
    Args:
        user_id: Supabase user ID
        session_token: Access token for authentication
    
    Returns:
        Salt bytes (16 bytes)
    """
    sb = get_client()
    
    # Set session for authenticated requests
    sb.auth.set_session(session_token, None)
    
    # Try to get existing salt
    try:
        res = sb.table("users_meta").select("salt").eq("id", user_id).execute()
        
        if res.data and len(res.data) > 0 and res.data[0].get("salt"):
            # Salt exists, decode from base64
            salt_b64 = res.data[0]["salt"]
            if isinstance(salt_b64, str):
                return ub64(salt_b64)
            # If it's already bytes, return as-is (Supabase might return bytea as bytes)
            return salt_b64 if isinstance(salt_b64, bytes) else ub64(str(salt_b64))
    except Exception:
        # User meta doesn't exist or salt not found, create it
        pass
    
    # Create new salt
    salt = gen_salt()
    salt_b64 = b64(salt)
    
    # Upsert user_meta with salt
    try:
        sb.table("users_meta").upsert({
            "id": user_id,
            "salt": salt_b64
        }).execute()
    except Exception as e:
        # If upsert fails, try insert
        try:
            sb.table("users_meta").insert({
                "id": user_id,
                "salt": salt_b64
            }).execute()
        except Exception:
            # If insert also fails (e.g., RLS issue), raise original error
            raise RuntimeError(f"Failed to create user salt: {e}")
    
    return salt


def list_all_local_snippets() -> List[Tuple[str, str]]:
    """
    List all local snippets with their full paths and decrypted content.
    
    Returns:
        List of tuples (full_path, content)
    """
    snippet_paths = db.list_snippets()
    snippets = []
    
    for path in snippet_paths:
        snippet = db.get_snippet(path)
        if snippet:
            snippets.append((path, snippet.content))
    
    return snippets


def sync_push(passphrase: str) -> Tuple[int, int]:
    """
    Push local snippets to Supabase (encrypted).
    
    Args:
        passphrase: User passphrase for encryption
    
    Returns:
        Tuple of (pushed_count, error_count)
    
    Raises:
        RuntimeError: If not authenticated or sync fails
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    access_token = session["access_token"]
    
    # Get or create user salt
    with console.status("[cyan]Setting up encryption...[/cyan]"):
        salt = ensure_user_salt(user_id, access_token)
    
    # Derive encryption key
    key = derive_key(passphrase, salt)
    
    # Get all local snippets
    local_snippets = list_all_local_snippets()
    
    if not local_snippets:
        console.print("[yellow]No local snippets to sync.[/yellow]")
        return (0, 0)
    
    sb = get_client()
    sb.auth.set_session(access_token, None)
    
    pushed_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Pushing snippets...", total=len(local_snippets))
        
        for full_path, content in local_snippets:
            try:
                # Parse module and name from full path
                if "/" in full_path:
                    parts = full_path.split("/")
                    module = "/".join(parts[:-1])
                    name = parts[-1]
                else:
                    module = None
                    name = full_path
                
                # Encrypt content
                content_bytes = content.encode('utf-8')
                ciphertext, nonce = encrypt(content_bytes, key)
                
                # Prepare data for Supabase
                snippet_data = {
                    "user_id": user_id,
                    "module": module,
                    "name": name,
                    "content_encrypted": ciphertext,  # Supabase handles bytes -> bytea
                    "nonce": nonce,
                    "salt": salt  # Store salt per snippet (or use user salt)
                }
                
                # Upsert to Supabase (update if exists, insert if not)
                # Note: Supabase upsert uses the unique constraint automatically
                sb.table("snippets").upsert(snippet_data).execute()
                
                pushed_count += 1
                progress.update(task, advance=1)
                
            except Exception as e:
                error_count += 1
                console.print(f"[red]Error pushing '{full_path}': {e}[/red]")
                progress.update(task, advance=1)
    
    # Update device last_sync (optional - create device entry if needed)
    try:
        import socket
        device_name = socket.gethostname()
        
        # Try to get existing device or create new one
        device_res = sb.table("devices").select("id").eq("user_id", user_id).eq("name", device_name).execute()
        
        from datetime import datetime
        device_data = {
            "user_id": user_id,
            "name": device_name,
            "last_sync": datetime.utcnow().isoformat()
        }
        
        if device_res.data and len(device_res.data) > 0:
            device_id = device_res.data[0]["id"]
            sb.table("devices").update(device_data).eq("id", device_id).execute()
        else:
            sb.table("devices").insert(device_data).execute()
    except Exception:
        # Device tracking is optional, don't fail if it errors
        pass
    
    return (pushed_count, error_count)


def sync_pull(passphrase: str) -> Tuple[int, int]:
    """
    Pull snippets from Supabase and decrypt into local database.
    
    Args:
        passphrase: User passphrase for decryption
    
    Returns:
        Tuple of (pulled_count, error_count)
    
    Raises:
        RuntimeError: If not authenticated or sync fails
    """
    if not is_authenticated():
        raise RuntimeError("Not logged in. Run 'snip auth login' first.")
    
    session = load_session()
    if not session:
        raise RuntimeError("Session not found. Please log in again.")
    
    user_id = session["user"]["id"]
    access_token = session["access_token"]
    
    # Get user salt
    with console.status("[cyan]Setting up decryption...[/cyan]"):
        salt = ensure_user_salt(user_id, access_token)
    
    # Derive decryption key
    key = derive_key(passphrase, salt)
    
    sb = get_client()
    sb.auth.set_session(access_token, None)
    
    # Fetch all snippets from Supabase
    try:
        response = sb.table("snippets").select("*").eq("user_id", user_id).execute()
        remote_snippets = response.data
    except Exception as e:
        raise RuntimeError(f"Failed to fetch snippets from server: {e}")
    
    if not remote_snippets:
        console.print("[yellow]No snippets found on server.[/yellow]")
        return (0, 0)
    
    pulled_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Pulling snippets...", total=len(remote_snippets))
        
        for row in remote_snippets:
            try:
                # Extract data
                module = row.get("module")
                name = row.get("name")
                content_encrypted = row["content_encrypted"]
                nonce = row["nonce"]
                
                # Build full path
                if module:
                    full_path = f"{module}/{name}"
                else:
                    full_path = name
                
                # Handle bytea data - Supabase might return as bytes or base64 string
                if isinstance(content_encrypted, str):
                    # Assume base64 encoded
                    ciphertext = ub64(content_encrypted)
                else:
                    ciphertext = content_encrypted
                
                if isinstance(nonce, str):
                    nonce_bytes = ub64(nonce)
                else:
                    nonce_bytes = nonce
                
                # Decrypt content
                try:
                    plaintext_bytes = decrypt(ciphertext, nonce_bytes, key)
                    content = plaintext_bytes.decode('utf-8')
                except Exception as e:
                    error_count += 1
                    console.print(f"[red]Decryption failed for '{full_path}': {e}[/red]")
                    console.print("[yellow]This usually means the passphrase is incorrect.[/yellow]")
                    progress.update(task, advance=1)
                    continue
                
                # Save to local database
                db.save_snippet(full_path, content)
                
                pulled_count += 1
                progress.update(task, advance=1)
                
            except Exception as e:
                error_count += 1
                console.print(f"[red]Error pulling '{row.get('name', 'unknown')}': {e}[/red]")
                progress.update(task, advance=1)
    
    return (pulled_count, error_count)

