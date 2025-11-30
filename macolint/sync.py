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
    # Use empty string for refresh_token if not available (Supabase requires string, not None)
    session = load_session()
    refresh_token = session.get("refresh_token", "") if session else ""
    sb.auth.set_session(session_token, refresh_token)
    
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
    # Use saved refresh_token or empty string (Supabase requires string, not None)
    refresh_token = session.get("refresh_token", "") if session else ""
    sb.auth.set_session(access_token, refresh_token)
    
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
                # Encode bytes to base64 strings for JSON serialization
                snippet_data = {
                    "user_id": user_id,
                    "module": module,
                    "name": name,
                    "content_encrypted": b64(ciphertext),  # Base64 encode for JSON
                    "nonce": b64(nonce),  # Base64 encode for JSON
                    "salt": b64(salt)  # Base64 encode for JSON
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
    
    # Get user salt (for backward compatibility, but we'll use snippet-specific salt if available)
    with console.status("[cyan]Setting up decryption...[/cyan]"):
        user_salt = ensure_user_salt(user_id, access_token)
    
    sb = get_client()
    # Use saved refresh_token or empty string (Supabase requires string, not None)
    refresh_token = session.get("refresh_token", "") if session else ""
    sb.auth.set_session(access_token, refresh_token)
    
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
                snippet_salt = row.get("salt")  # Salt stored with this snippet
                
                # Build full path
                if module:
                    full_path = f"{module}/{name}"
                else:
                    full_path = name
                
                # Handle Supabase returning bytea as {"type":"Buffer","data":[...]}
                # The column is BYTEA, but we store base64 strings, so Supabase stores
                # the UTF-8 bytes of the base64 string
                try:
                    import re
                    
                    def normalize_base64(s: str) -> str:
                        """Normalize a base64 string by removing invalid characters and fixing padding."""
                        # Remove all whitespace
                        s = re.sub(r'\s+', '', s)
                        # Remove any non-base64 characters
                        s = re.sub(r'[^A-Za-z0-9+/=]', '', s)
                        # Remove padding from the end, we'll add it back correctly
                        data_part = s.rstrip('=')
                        # Fix padding: base64 strings should be multiples of 4
                        missing_padding = len(data_part) % 4
                        if missing_padding:
                            data_part += '=' * (4 - missing_padding)
                        return data_part
                    
                    def buffer_to_bytes(value):
                        if isinstance(value, dict) and value.get("type") == "Buffer":
                            buffer_bytes = bytes(value["data"])
                            
                            # Decode as UTF-8 string (the base64 string we stored)
                            try:
                                base64_str = buffer_bytes.decode('utf-8')
                            except UnicodeDecodeError as e:
                                raise ValueError(
                                    f"Failed to decode Buffer as UTF-8: {e}. "
                                    f"Buffer has {len(buffer_bytes)} bytes. "
                                    f"First 20 bytes: {list(buffer_bytes[:20])}"
                                ) from e
                            
                            # Normalize and decode
                            try:
                                normalized = normalize_base64(base64_str)
                                
                                if len(normalized) % 4 != 0:
                                    raise ValueError(
                                        f"Normalized base64 string length ({len(normalized)}) is not a multiple of 4. "
                                        f"Original string length: {len(base64_str)}, "
                                        f"Buffer bytes: {len(buffer_bytes)}"
                                    )
                                
                                # Try to decode, catch base64 errors specifically
                                try:
                                    result = ub64(normalized)
                                    return result
                                except Exception as decode_err:
                                    error_str = str(decode_err)
                                    data_chars = len(normalized.rstrip('='))
                                    
                                    # If it's the 137 character error, try to fix it
                                    if "cannot be 1 more than a multiple of 4" in error_str or (data_chars % 4 == 1):
                                        # Remove last non-padding character
                                        if normalized and normalized[-1] != '=':
                                            fixed = normalized[:-1]
                                        else:
                                            # Find last non-padding char
                                            fixed = normalized.rstrip('=')
                                            if len(fixed) > 0:
                                                fixed = fixed[:-1]
                                        # Re-add padding
                                        missing_padding = len(fixed) % 4
                                        if missing_padding:
                                            fixed += '=' * (4 - missing_padding)
                                        try:
                                            result = ub64(fixed)
                                            return result
                                        except Exception as e2:
                                            raise decode_err from e2
                                    raise
                            except Exception as e:
                                raise ValueError(f"Failed to decode base64: {e}") from e
                        if isinstance(value, str):
                            import binascii
                            
                            # The string from Supabase might be hex-encoded bytes of the base64 string
                            # Check if it starts with literal \x (escaped backslash-x)
                            processed_value = value
                            if value.startswith('\\x'):
                                # Remove the \x prefix
                                hex_str = value[2:]
                                
                                # Try decoding as hex first (hex representation of UTF-8 bytes of base64 string)
                                try:
                                    # Decode hex to get the UTF-8 bytes of the base64 string
                                    utf8_bytes = bytes.fromhex(hex_str)
                                    # Decode UTF-8 to get the actual base64 string
                                    processed_value = utf8_bytes.decode('utf-8')
                                except Exception:
                                    # If hex decode fails, treat the hex string itself as base64
                                    processed_value = hex_str
                            
                            base64_str = normalize_base64(processed_value)
                            
                            if len(base64_str) % 4 != 0:
                                raise ValueError(f"Invalid base64 string length: {len(base64_str)} characters")
                            
                            # Count non-padding characters
                            data_chars = len(base64_str.rstrip('='))
                            
                            # Try to decode, catch base64 errors specifically
                            try:
                                result = ub64(base64_str)
                                return result
                            except (Exception, binascii.Error) as decode_err:
                                error_str = str(decode_err)
                                
                                # If it's the 137 character error (or any "1 more than multiple of 4"), try to fix it
                                if "cannot be 1 more than a multiple of 4" in error_str or (data_chars % 4 == 1):
                                    # Strategy: Truncate to the nearest multiple of 4 for data chars
                                    chars_to_remove = data_chars % 4
                                    if chars_to_remove > 0:
                                        # Remove from the data part (before padding)
                                        data_part = base64_str.rstrip('=')
                                        # Remove the last N characters from data part
                                        fixed_data = data_part[:-chars_to_remove]
                                        # Recalculate padding
                                        missing_padding = len(fixed_data) % 4
                                        if missing_padding:
                                            fixed = fixed_data + '=' * (4 - missing_padding)
                                        else:
                                            fixed = fixed_data
                                        
                                        try:
                                            result = ub64(fixed)
                                            return result
                                        except Exception as e2:
                                            raise decode_err from e2
                                raise
                        if isinstance(value, bytes):
                            # Try to decode as UTF-8 string first (base64 string)
                            try:
                                base64_str = value.decode('utf-8')
                                base64_str = normalize_base64(base64_str)
                                if len(base64_str) % 4 != 0:
                                    raise ValueError(f"Invalid base64 string length: {len(base64_str)} characters")
                                return ub64(base64_str)
                            except (UnicodeDecodeError, ValueError):
                                # If it's not valid UTF-8, assume it's already raw bytes
                                return value
                        raise ValueError(f"Unsupported type for encrypted content: {type(value)}")

                    ciphertext = buffer_to_bytes(content_encrypted)
                    nonce_bytes = buffer_to_bytes(nonce)
                    
                    # Handle salt - use snippet-specific salt if available, otherwise fall back to user salt
                    if snippet_salt:
                        salt_bytes = buffer_to_bytes(snippet_salt)
                    else:
                        salt_bytes = user_salt
                    
                    # Derive decryption key for this snippet
                    snippet_key = derive_key(passphrase, salt_bytes)
                except Exception as e:
                    error_count += 1
                    console.print(f"[red]Invalid encrypted content for '{full_path}': {e}[/red]")
                    progress.update(task, advance=1)
                    continue
                
                # Decrypt content
                try:
                    plaintext_bytes = decrypt(ciphertext, nonce_bytes, snippet_key)
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

