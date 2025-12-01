-- ============================================================================
-- UPDATE TEAMS INSERT POLICY - Run this in Supabase SQL Editor
-- ============================================================================
-- This fixes the "new row violates row-level security policy" error
-- ============================================================================

-- Drop the existing policy
DROP POLICY IF EXISTS "Users can create teams" ON teams;

-- Create new policy with TO authenticated clause
-- This ensures PostgREST properly recognizes authenticated users
CREATE POLICY "Users can create teams"
    ON teams
    FOR INSERT
    TO authenticated
    WITH CHECK (
        -- User must be authenticated
        -- created_by will automatically be set to auth.uid() via DEFAULT
        auth.uid() IS NOT NULL
    );

-- Verify the policy was created
SELECT 
    policyname,
    cmd,
    roles,
    with_check
FROM pg_policies 
WHERE tablename = 'teams' AND policyname = 'Users can create teams';

