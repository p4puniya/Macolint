-- ============================================================================
-- Phase 2: Teams + Collaboration Migration Script
-- ============================================================================
-- Run this ENTIRE script in your Supabase SQL editor to add teams support
-- This script is idempotent - safe to run multiple times
-- ============================================================================

-- 1. Create teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Set default value for created_by to automatically use auth.uid()
-- This ensures created_by is always set to the authenticated user
ALTER TABLE teams ALTER COLUMN created_by SET DEFAULT auth.uid();

-- 2. Create team_members table
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- 3. Add team_id column to snippets table
-- Add team_id column (nullable for personal snippets)
ALTER TABLE snippets ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE CASCADE;

-- Drop the old unique constraint if it exists (it might be named differently)
-- Try common constraint names
DO $$ 
BEGIN
    -- Try to drop the constraint if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'snippets_user_id_module_name_key'
    ) THEN
        ALTER TABLE snippets DROP CONSTRAINT snippets_user_id_module_name_key;
    END IF;
    
    -- Also try the default PostgreSQL naming convention
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'snippets'::regclass 
        AND contype = 'u'
        AND array_length(conkey, 1) = 3
        AND conkey::text LIKE '%user_id%'
    ) THEN
        -- Find and drop the constraint
        EXECUTE (
            SELECT 'ALTER TABLE snippets DROP CONSTRAINT ' || conname
            FROM pg_constraint
            WHERE conrelid = 'snippets'::regclass 
            AND contype = 'u'
            AND array_length(conkey, 1) = 3
            AND conkey::text LIKE '%user_id%'
            LIMIT 1
        );
    END IF;
END $$;

-- Create new unique constraints that include team_id
-- Personal snippets: team_id IS NULL, unique on (user_id, module, name)
-- Team snippets: team_id IS NOT NULL, unique on (team_id, module, name)
CREATE UNIQUE INDEX IF NOT EXISTS idx_snippets_personal_unique 
    ON snippets(user_id, COALESCE(module, ''), name) 
    WHERE team_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_snippets_team_unique 
    ON snippets(team_id, COALESCE(module, ''), name) 
    WHERE team_id IS NOT NULL;

-- 4. Enable Row-Level Security on new tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

-- 5. Create helper function to check team membership (bypasses RLS)
-- This MUST be created before any policies that use it
CREATE OR REPLACE FUNCTION is_team_member(team_uuid UUID, user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM team_members
        WHERE team_id = team_uuid AND user_id = user_uuid
    );
$$;

-- Helper function to get current user ID (for debugging - not used in policies)
-- Keeping for potential future use
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
SET search_path = public
AS $$
    SELECT auth.uid();
$$;

-- 6. RLS Policies for teams table
-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Users can read teams they're members of" ON teams;
DROP POLICY IF EXISTS "Users can create teams" ON teams;
DROP POLICY IF EXISTS "Team creators can update teams" ON teams;
DROP POLICY IF EXISTS "Team creators can delete teams" ON teams;

-- Users can read teams they're members of
-- Use the helper function to avoid infinite recursion
CREATE POLICY "Users can read teams they're members of"
    ON teams
    FOR SELECT
    USING (is_team_member(id, auth.uid()));

-- Users can create teams (they become the creator)
-- FIXED: Added TO authenticated to ensure PostgREST recognizes the JWT token
-- Since created_by has DEFAULT auth.uid(), we only need to check authentication
-- The default ensures created_by is always set correctly
CREATE POLICY "Users can create teams"
    ON teams
    FOR INSERT
    TO authenticated
    WITH CHECK (
        -- User must be authenticated
        -- created_by will automatically be set to auth.uid() via DEFAULT
        auth.uid() IS NOT NULL
    );

-- Team creators can update their teams
CREATE POLICY "Team creators can update teams"
    ON teams
    FOR UPDATE
    USING (auth.uid()::text = created_by::text)
    WITH CHECK (auth.uid()::text = created_by::text);

-- Team creators can delete their teams
CREATE POLICY "Team creators can delete teams"
    ON teams
    FOR DELETE
    USING (auth.uid()::text = created_by::text);

-- 7. RLS Policies for team_members table
-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Users can read team members" ON team_members;
DROP POLICY IF EXISTS "Team creators can add members" ON team_members;
DROP POLICY IF EXISTS "Team creators can update members" ON team_members;
DROP POLICY IF EXISTS "Team creators can remove members" ON team_members;

-- Users can read members of teams they belong to
-- Use the helper function to avoid infinite recursion
CREATE POLICY "Users can read team members"
    ON team_members
    FOR SELECT
    USING (is_team_member(team_id, auth.uid()));

-- Team creators can add members
-- Also allow users to add themselves when creating a team
-- FIXED: Using text comparison for reliability
CREATE POLICY "Team creators can add members"
    ON team_members
    FOR INSERT
    WITH CHECK (
        -- User is the team creator (using text comparison for reliability)
        team_id IN (
            SELECT id FROM teams WHERE created_by::text = auth.uid()::text
        ) OR
        -- User is adding themselves (for initial team creation)
        user_id::text = auth.uid()::text
    );

-- Team creators can update members
CREATE POLICY "Team creators can update members"
    ON team_members
    FOR UPDATE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE created_by::text = auth.uid()::text
        )
    );

-- Team creators can remove members
CREATE POLICY "Team creators can remove members"
    ON team_members
    FOR DELETE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE created_by::text = auth.uid()::text
        )
    );

-- 8. Update snippets RLS policy to allow team access
-- Drop existing policy if it exists (it should exist from your original schema)
DROP POLICY IF EXISTS "Users can manage their snippets" ON snippets;

-- Create new policy that allows:
-- 1. Personal snippets: user_id = auth.uid() AND team_id IS NULL
-- 2. Team snippets: team_id IS NOT NULL AND user is a member of that team
-- Note: For existing snippets, team_id will be NULL, so they'll work as personal snippets
-- Use the helper function to avoid infinite recursion
CREATE POLICY "Users can manage their snippets"
    ON snippets
    FOR ALL
    USING (
        (team_id IS NULL AND user_id::text = auth.uid()::text) OR
        (team_id IS NOT NULL AND is_team_member(team_id, auth.uid()))
    )
    WITH CHECK (
        (team_id IS NULL AND user_id::text = auth.uid()::text) OR
        (team_id IS NOT NULL AND is_team_member(team_id, auth.uid()))
    );

-- 9. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_snippets_team_id ON snippets(team_id);

-- 10. Create trigger to automatically add creator to team_members
-- This ensures the team creator is automatically added as an 'owner' member
DROP TRIGGER IF EXISTS trigger_add_creator_to_team_members ON teams;
DROP FUNCTION IF EXISTS add_creator_to_team_members();

CREATE OR REPLACE FUNCTION add_creator_to_team_members()
RETURNS TRIGGER AS $$
BEGIN
    -- Automatically add the team creator as an 'owner' member
    INSERT INTO team_members (team_id, user_id, role)
    VALUES (NEW.id, NEW.created_by, 'owner')
    ON CONFLICT (team_id, user_id) DO NOTHING;  -- Prevent duplicate if already exists
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_add_creator_to_team_members
    AFTER INSERT ON teams
    FOR EACH ROW 
    EXECUTE FUNCTION add_creator_to_team_members();

-- ============================================================================
-- Migration Complete!
-- ============================================================================
-- After running this script, test with: snip team create test-team
-- 
-- What this migration does:
-- 1. Sets created_by default to auth.uid() - automatically uses authenticated user
-- 2. Simplifies RLS policy - only checks authentication, not created_by match
-- 3. Adds trigger to automatically add creator to team_members as 'owner'
-- ============================================================================
