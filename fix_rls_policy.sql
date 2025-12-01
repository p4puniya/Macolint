-- ============================================================================
-- FIX FOR RLS POLICY ISSUE - Run this in Supabase SQL Editor
-- ============================================================================
-- This fixes the "new row violates row-level security policy" error
-- when creating teams via the Python client
-- ============================================================================

-- Step 1: Check current policy (for debugging)
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    permissive, 
    roles, 
    cmd, 
    qual, 
    with_check
FROM pg_policies 
WHERE tablename = 'teams' AND policyname = 'Users can create teams';

-- Step 2: Drop the existing policy
DROP POLICY IF EXISTS "Users can create teams" ON teams;

-- Step 3: Create new policy with text comparison (more reliable for UUID comparison)
-- This ensures the comparison works correctly regardless of how the UUID is sent
CREATE POLICY "Users can create teams"
    ON teams
    FOR INSERT
    WITH CHECK (
        -- User must be authenticated
        auth.uid() IS NOT NULL AND
        -- User must be setting themselves as the creator
        -- Using text comparison to avoid UUID type casting issues
        auth.uid()::text = created_by::text
    );

-- Step 4: Verify the policy was created
SELECT 
    policyname,
    cmd,
    with_check
FROM pg_policies 
WHERE tablename = 'teams' AND policyname = 'Users can create teams';

-- ============================================================================
-- ALTERNATIVE: If the above doesn't work, try this simpler policy:
-- ============================================================================
/*
DROP POLICY IF EXISTS "Users can create teams" ON teams;

CREATE POLICY "Users can create teams"
    ON teams
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = created_by);
*/

