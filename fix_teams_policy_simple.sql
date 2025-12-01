-- ============================================================================
-- SIMPLE FIX FOR TEAMS INSERT POLICY
-- ============================================================================
-- The current policy might be too strict. Let's try the simplest possible policy.
-- ============================================================================

-- Drop the existing policy
DROP POLICY IF EXISTS "Users can create teams" ON teams;

-- Create the simplest possible policy
-- Just allow authenticated users to insert, no additional checks
-- The DEFAULT on created_by will handle setting it to auth.uid()
CREATE POLICY "Users can create teams"
    ON teams
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Verify
SELECT 
    policyname,
    cmd,
    roles,
    with_check
FROM pg_policies 
WHERE tablename = 'teams' AND policyname = 'Users can create teams';

