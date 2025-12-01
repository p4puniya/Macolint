-- ============================================================================
-- Function to get user ID by email address
-- ============================================================================
-- This function allows authenticated users to look up other users by email
-- for the purpose of adding them to teams.
-- ============================================================================

-- Drop function if it exists (for idempotency)
DROP FUNCTION IF EXISTS public.get_user_id_by_email(TEXT);

-- Create function to get user ID by email
-- Must be in public schema for PostgREST to find it
-- Using SECURITY DEFINER to allow access to auth.users table
CREATE OR REPLACE FUNCTION public.get_user_id_by_email(user_email TEXT)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, public
AS $$
DECLARE
    user_uuid UUID;
BEGIN
    -- Query auth.users table to find user by email
    -- Using SECURITY DEFINER allows this function to access auth schema
    SELECT id INTO user_uuid
    FROM auth.users
    WHERE email = LOWER(TRIM(user_email))
    LIMIT 1;
    
    RETURN user_uuid;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.get_user_id_by_email(TEXT) TO authenticated;

-- Also grant to anon role (if needed for some setups)
GRANT EXECUTE ON FUNCTION public.get_user_id_by_email(TEXT) TO anon;

-- Add comment
COMMENT ON FUNCTION public.get_user_id_by_email(TEXT) IS 
'Returns the user ID (UUID) for a given email address. Used for adding users to teams.';

-- Verify the function was created
SELECT 
    routine_name,
    routine_schema,
    data_type as return_type
FROM information_schema.routines
WHERE routine_name = 'get_user_id_by_email'
AND routine_schema = 'public';

