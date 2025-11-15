-- Redesign credentials architecture to support multiple credentials per platform
-- and link apps to specific credentials

-- =============================================================================
-- Step 1: Modify credentials table
-- =============================================================================

-- Remove the unique constraint on platform to allow multiple credentials per platform
alter table credentials drop constraint if exists credentials_platform_key;

-- Add name field to identify different credentials
alter table credentials add column if not exists name text;

-- Set default names for existing credentials (if any)
update credentials set name =
  case
    when platform = 'ios' then 'iOS 主账号'
    when platform = 'android' then 'Android 主账号'
  end
where name is null;

-- Make name required
alter table credentials alter column name set not null;

-- Add unique constraint on platform + name combination
alter table credentials add constraint credentials_platform_name_unique
  unique (platform, name);

-- Add index on name for faster lookups
create index if not exists idx_credentials_name on credentials(name);

comment on column credentials.name is 'Credential name for identification (e.g., "Main iOS Account", "Partner Android Account")';

-- =============================================================================
-- Step 2: Add credential_id to apps table
-- =============================================================================

-- Add credential_id column to apps table
alter table apps add column if not exists credential_id bigint;

-- Add foreign key constraint
alter table apps add constraint fk_apps_credential
  foreign key (credential_id) references credentials(id)
  on delete set null;

-- Add index for faster lookups
create index if not exists idx_apps_credential on apps(credential_id);

comment on column apps.credential_id is 'Associated credential for API access. Apps without credentials cannot fetch data.';

-- =============================================================================
-- Step 3: Add validation function
-- =============================================================================

-- Function to validate app activation based on credential
create or replace function validate_app_activation()
returns trigger as $$
begin
  -- If trying to activate app without credential, prevent it
  if new.is_active = true and new.credential_id is null then
    raise exception 'Cannot activate app without associated credential. Please select a credential first.';
  end if;

  return new;
end;
$$ language plpgsql;

-- Add trigger to validate app activation
drop trigger if exists check_app_activation on apps;
create trigger check_app_activation
  before insert or update on apps
  for each row
  execute function validate_app_activation();

-- =============================================================================
-- Step 4: Update existing apps (if any)
-- =============================================================================

-- Try to auto-associate existing apps with credentials based on platform
-- This is a one-time migration for existing data
do $$
declare
  ios_cred_id bigint;
  android_cred_id bigint;
begin
  -- Get iOS credential id (if exists)
  select id into ios_cred_id from credentials where platform = 'ios' limit 1;

  -- Get Android credential id (if exists)
  select id into android_cred_id from credentials where platform = 'android' limit 1;

  -- Associate iOS apps with iOS credential
  if ios_cred_id is not null then
    update apps set credential_id = ios_cred_id
    where platform = 'ios' and credential_id is null;
  end if;

  -- Associate Android apps with Android credential
  if android_cred_id is not null then
    update apps set credential_id = android_cred_id
    where platform = 'android' and credential_id is null;
  end if;

  -- Deactivate apps without credentials
  update apps set is_active = false
  where credential_id is null and is_active = true;
end $$;

-- =============================================================================
-- Step 5: Add helper view for credential usage
-- =============================================================================

-- View to show credential usage statistics
create or replace view credential_usage as
select
  c.id,
  c.name,
  c.platform,
  c.is_active,
  c.created_at,
  c.updated_at,
  count(a.id) as app_count,
  count(a.id) filter (where a.is_active = true) as active_app_count
from credentials c
left join apps a on a.credential_id = c.id
group by c.id, c.name, c.platform, c.is_active, c.created_at, c.updated_at;

comment on view credential_usage is 'Shows credential usage statistics including number of associated apps';
