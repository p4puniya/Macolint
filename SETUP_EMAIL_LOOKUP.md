# Setup Email Lookup for Team Add Command

## Quick Setup

To enable adding team members by email address, you need to create a database function in Supabase.

### Steps:

1. **Open Supabase Dashboard**
   - Go to https://app.supabase.com
   - Select your project

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Copy and Paste the SQL**
   - Open `get_user_by_email_function.sql` in this directory
   - Copy ALL the contents
   - Paste into the SQL Editor

4. **Run the SQL**
   - Click the "Run" button (or press Cmd/Ctrl + Enter)
   - You should see a success message

5. **Verify it Works**
   - Try: `snip team add <team-name> <email>`
   - It should now work!

### What This Does

Creates a function `get_user_id_by_email()` that:
- Takes an email address as input
- Returns the user's UUID from `auth.users`
- Allows authenticated users to look up other users by email
- Required for the `snip team add` command to work with email addresses

### Troubleshooting

If you get "function not found" error:
- Make sure you ran the SQL in the Supabase SQL Editor
- Check that the function was created: Run `SELECT routine_name FROM information_schema.routines WHERE routine_name = 'get_user_id_by_email';`
- Make sure you're logged in: `snip auth login`

