-- Admin accounts and Google sign-in.
-- * admins: emails that get every fighter, every bonus skill, all emblems at max level and a
--   big wallet. Applied when the account is created and re-applied on every profile load, so
--   fighters added later are unlocked too. No client can read or write this table.
-- * Google sign-ups have no "username" in their metadata: use their Google name instead.

create table if not exists public.admins (email text primary key);
alter table public.admins enable row level security;
insert into public.admins (email) values ('jaynesadibo@gmail.com') on conflict do nothing;

create or replace function public.all_characters() returns text[] language sql immutable as $$
  select array['aster','vesper','garrick','kaede','ember','marina','nyx','rook','kira',
               'raven','ash','gale']
$$;

-- Unlocks everything for an admin's profile; no-op for everyone else.
create or replace function public.apply_admin(p_uid uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from admins a join auth.users u on lower(u.email) = lower(a.email) where u.id = p_uid) then
    return;
  end if;
  update profiles set
    characters = all_characters(),
    skills = all_characters(),
    emblems = '{"fighter":10,"tank":10,"assassin":10,"mage":10,"swift":10}'::jsonb,
    gold = greatest(gold, 999999),
    diamonds = greatest(diamonds, 99999)
  where id = p_uid;
end $$;
revoke all on function public.apply_admin(uuid) from public, anon, authenticated;

-- Profile on sign-up: username from the form, else the Google name, else the email.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  raw text := coalesce(new.raw_user_meta_data ->> 'username', new.raw_user_meta_data ->> 'full_name',
                       new.raw_user_meta_data ->> 'name', split_part(new.email, '@', 1), 'Player');
  base text := coalesce(nullif(regexp_replace(raw, '[^A-Za-z0-9_]', '', 'g'), ''), 'Player');
  name text := left(base, 12);
begin
  if exists (select 1 from profiles where lower(username) = lower(name)) or char_length(name) < 2 then
    name := left(base, 10) || floor(random() * 9000 + 1000)::text;
  end if;
  insert into profiles (id, username) values (new.id, name);
  perform apply_admin(new.id);
  return new;
end $$;

-- Called by the client after sign-in: re-applies admin unlocks and returns the profile.
create or replace function public.my_profile() returns profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  perform apply_admin(auth.uid());
  select * into p from profiles where id = auth.uid();
  return p;
end $$;
grant execute on function public.my_profile() to authenticated;

-- Existing admin accounts get their unlocks right away.
select public.apply_admin(u.id) from auth.users u join public.admins a on lower(u.email) = lower(a.email);
