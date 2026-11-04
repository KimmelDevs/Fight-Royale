-- Fight Royale accounts and economy.
-- Players can read their own rows but never write them directly: every change to gold,
-- diamonds, unlocks, emblems and bets goes through the security-definer functions below,
-- which enforce prices and reward caps.

create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  username text unique check (char_length(username) between 2 and 16),
  gold bigint not null default 0 check (gold >= 0),
  diamonds bigint not null default 0 check (diamonds >= 0),
  characters text[] not null default array['aster', 'vesper', 'ember'],
  skills text[] not null default '{}',           -- characters whose bonus skill is unlocked
  loadouts jsonb not null default '{}'::jsonb,   -- character id -> ["z","x","c"] slots
  emblems jsonb not null default '{}'::jsonb,    -- emblem id -> level (missing = 1)
  emblem text not null default 'fighter',
  reward_day date not null default current_date,
  reward_today int not null default 0,
  last_reward_at timestamptz,
  ads_day date not null default current_date,
  ads_today int not null default 0,
  last_ad_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
create policy "read own profile" on public.profiles for select using (auth.uid() = id);

-- Create a profile for every new account.
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  base text := coalesce(nullif(regexp_replace(new.raw_user_meta_data ->> 'username', '[^A-Za-z0-9_]', '', 'g'), ''), 'Player');
  name text := left(base, 12);
begin
  if exists (select 1 from profiles where lower(username) = lower(name)) or char_length(name) < 2 then
    name := left(base, 10) || floor(random() * 9000 + 1000)::text;
  end if;
  insert into profiles (id, username) values (new.id, name);
  return new;
end $$;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- --- catalog -----------------------------------------------------------------------
create function public.valid_character(c text) returns boolean language sql immutable as $$
  select c = any (array['aster','vesper','garrick','kaede','ember','marina','volta','sylva','nyx','rook','kira'])
$$;

create function public.valid_emblem(e text) returns boolean language sql immutable as $$
  select e = any (array['fighter','tank','assassin','mage','swift'])
$$;

-- --- purchases with in-game currency ---------------------------------------------------
create function public.buy_character(p_char text, p_currency text) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if not valid_character(p_char) then raise exception 'unknown character'; end if;
  select * into p from profiles where id = auth.uid() for update;
  if p.id is null then raise exception 'no profile'; end if;
  if p_char = any (p.characters) then return p; end if;
  if p_currency = 'gold' then
    if p.gold < 5000 then raise exception 'not enough gold'; end if;
    update profiles set gold = gold - 5000, characters = array_append(characters, p_char) where id = p.id returning * into p;
  elsif p_currency = 'diamonds' then
    if p.diamonds < 250 then raise exception 'not enough diamonds'; end if;
    update profiles set diamonds = diamonds - 250, characters = array_append(characters, p_char) where id = p.id returning * into p;
  else raise exception 'bad currency'; end if;
  return p;
end $$;

create function public.buy_skill(p_char text, p_currency text) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if not valid_character(p_char) then raise exception 'unknown character'; end if;
  select * into p from profiles where id = auth.uid() for update;
  if p.id is null then raise exception 'no profile'; end if;
  if p_char = any (p.skills) then return p; end if;
  if p_currency = 'gold' then
    if p.gold < 2000 then raise exception 'not enough gold'; end if;
    update profiles set gold = gold - 2000, skills = array_append(skills, p_char) where id = p.id returning * into p;
  elsif p_currency = 'diamonds' then
    if p.diamonds < 100 then raise exception 'not enough diamonds'; end if;
    update profiles set diamonds = diamonds - 100, skills = array_append(skills, p_char) where id = p.id returning * into p;
  else raise exception 'bad currency'; end if;
  return p;
end $$;

create function public.set_loadout(p_char text, p_slots text[]) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if not valid_character(p_char) then raise exception 'unknown character'; end if;
  if array_length(p_slots, 1) <> 3 or (select count(distinct s) from unnest(p_slots) s) <> 3
     or exists (select 1 from unnest(p_slots) s where s <> all (array['z','x','c','v'])) then
    raise exception 'loadout needs 3 different skills';
  end if;
  select * into p from profiles where id = auth.uid() for update;
  if 'v' = any (p_slots) and not (p_char = any (p.skills)) then raise exception 'skill locked'; end if;
  update profiles set loadouts = loadouts || jsonb_build_object(p_char, to_jsonb(p_slots)) where id = p.id returning * into p;
  return p;
end $$;

create function public.set_emblem(p_emblem text) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if not valid_emblem(p_emblem) then raise exception 'unknown emblem'; end if;
  update profiles set emblem = p_emblem where id = auth.uid() returning * into p;
  return p;
end $$;

-- Emblem upgrade: level L -> L+1 costs 300 * L gold, max level 10.
create function public.upgrade_emblem(p_emblem text) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles; lvl int; cost int;
begin
  if not valid_emblem(p_emblem) then raise exception 'unknown emblem'; end if;
  select * into p from profiles where id = auth.uid() for update;
  lvl := coalesce((p.emblems ->> p_emblem)::int, 1);
  if lvl >= 10 then raise exception 'emblem at max level'; end if;
  cost := 300 * lvl;
  if p.gold < cost then raise exception 'not enough gold'; end if;
  update profiles set gold = gold - cost, emblems = emblems || jsonb_build_object(p_emblem, lvl + 1)
    where id = p.id returning * into p;
  return p;
end $$;

create function public.set_username(p_name text) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if p_name !~ '^[A-Za-z0-9_]{2,16}$' then raise exception 'name must be 2-16 letters, numbers or _'; end if;
  update profiles set username = p_name where id = auth.uid() returning * into p;
  return p;
end $$;

-- --- rewards -----------------------------------------------------------------------------
-- Match results come from players' browsers, so rewards are capped: at most 3000 gold per
-- claim (250 for a duel or team win), one claim every 20 seconds, 30000 gold per day.
create function public.claim_reward(p_reason text, p_amount int) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles; cap int; amt int;
begin
  cap := case p_reason when 'duel' then 250 when 'team' then 250 when 'survival' then 3000 else 0 end;
  if cap = 0 then raise exception 'bad reward'; end if;
  amt := greatest(0, least(p_amount, cap));
  select * into p from profiles where id = auth.uid() for update;
  if p.id is null then raise exception 'no profile'; end if;
  if p.reward_day <> current_date then
    update profiles set reward_day = current_date, reward_today = 0 where id = p.id returning * into p;
  end if;
  if p.last_reward_at is not null and p.last_reward_at > now() - interval '20 seconds' then
    raise exception 'slow down';
  end if;
  amt := least(amt, 30000 - p.reward_today);
  update profiles set gold = gold + amt, reward_today = reward_today + amt, last_reward_at = now()
    where id = p.id returning * into p;
  return p;
end $$;

-- Rewarded ad: +5 diamonds, up to 10 per day, one per 30 seconds.
-- TODO before launch: verify completions server-side with the ad network (SSV callback).
create function public.ad_reward() returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  select * into p from profiles where id = auth.uid() for update;
  if p.id is null then raise exception 'no profile'; end if;
  if p.ads_day <> current_date then
    update profiles set ads_day = current_date, ads_today = 0 where id = p.id returning * into p;
  end if;
  if p.ads_today >= 10 then raise exception 'daily ad limit reached'; end if;
  if p.last_ad_at is not null and p.last_ad_at > now() - interval '30 seconds' then raise exception 'slow down'; end if;
  update profiles set diamonds = diamonds + 5, ads_today = ads_today + 1, last_ad_at = now()
    where id = p.id returning * into p;
  return p;
end $$;

-- --- gold bets for team matches ---------------------------------------------------------
-- Everyone stakes before the match. Afterwards each bettor reports the winner; when all
-- reports agree the pot is split among the winners by stake, otherwise everyone is refunded.
create table public.bets (
  match_id text not null,
  user_id uuid not null references public.profiles on delete cascade,
  team int not null,
  amount int not null check (amount between 1 and 5000),
  reported int,
  settled boolean not null default false,
  payout int,
  created_at timestamptz not null default now(),
  primary key (match_id, user_id)
);
alter table public.bets enable row level security;
create policy "read own bets" on public.bets for select using (auth.uid() = user_id);

create function public.place_bet(p_match text, p_team int, p_amount int) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  if p_amount < 1 or p_amount > 5000 then raise exception 'bet must be 1-5000 gold'; end if;
  select * into p from profiles where id = auth.uid() for update;
  if p.gold < p_amount then raise exception 'not enough gold'; end if;
  insert into bets (match_id, user_id, team, amount) values (p_match, p.id, p_team, p_amount);
  update profiles set gold = gold - p_amount where id = p.id returning * into p;
  return p;
end $$;

create function public.settle_match(p_match text) returns void
language plpgsql security definer set search_path = public as $$
declare winner int; agree boolean; pot int; wsum int;
begin
  perform 1 from bets where match_id = p_match and not settled for update;
  if exists (select 1 from bets where match_id = p_match and not settled and reported is null) then return; end if;
  select count(distinct reported) = 1, min(reported), sum(amount) into agree, winner, pot
    from bets where match_id = p_match and not settled;
  if pot is null then return; end if;
  select coalesce(sum(amount), 0) into wsum from bets where match_id = p_match and not settled and team = winner;
  if not agree or wsum = 0 then
    update bets set payout = amount where match_id = p_match and not settled;
  else
    update bets set payout = case when team = winner then floor(pot::numeric * amount / wsum)::int else 0 end
      where match_id = p_match and not settled;
  end if;
  update profiles pr set gold = pr.gold + b.payout
    from bets b where b.match_id = p_match and not b.settled and b.user_id = pr.id;
  update bets set settled = true where match_id = p_match and not settled;
end $$;

create function public.report_result(p_match text, p_winner int) returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles;
begin
  update bets set reported = p_winner where match_id = p_match and user_id = auth.uid() and not settled;
  perform settle_match(p_match);
  select * into p from profiles where id = auth.uid();
  return p;
end $$;

-- Refund the caller's bets that were never settled (someone left mid-match).
create function public.refund_stale_bets() returns public.profiles
language plpgsql security definer set search_path = public as $$
declare p profiles; m text;
begin
  for m in select distinct match_id from bets where user_id = auth.uid() and not settled and created_at < now() - interval '20 minutes' loop
    update profiles pr set gold = pr.gold + b.amount from bets b where b.match_id = m and not b.settled and b.user_id = pr.id;
    update bets set payout = amount, settled = true where match_id = m and not settled;
  end loop;
  select * into p from profiles where id = auth.uid();
  return p;
end $$;

-- --- diamond purchases (written only by the stripe-webhook Edge Function) ---------------
create table public.purchases (
  session_id text primary key,
  user_id uuid not null references public.profiles on delete cascade,
  diamonds int not null,
  created_at timestamptz not null default now()
);
alter table public.purchases enable row level security;
create policy "read own purchases" on public.purchases for select using (auth.uid() = user_id);

create function public.credit_purchase(p_session text, p_user uuid, p_diamonds int) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into purchases (session_id, user_id, diamonds) values (p_session, p_user, p_diamonds)
    on conflict (session_id) do nothing;
  if found then update profiles set diamonds = diamonds + p_diamonds where id = p_user; end if;
end $$;
revoke execute on function public.credit_purchase(text, uuid, int) from public, anon, authenticated;
revoke execute on function public.settle_match(text) from public, anon, authenticated;

-- Players call the rest only when signed in.
revoke execute on function public.buy_character(text, text), public.buy_skill(text, text), public.set_loadout(text, text[]),
  public.set_emblem(text), public.upgrade_emblem(text), public.set_username(text), public.claim_reward(text, int),
  public.ad_reward(), public.place_bet(text, int, int), public.report_result(text, int), public.refund_stale_bets()
  from public, anon;
grant execute on function public.buy_character(text, text), public.buy_skill(text, text), public.set_loadout(text, text[]),
  public.set_emblem(text), public.upgrade_emblem(text), public.set_username(text), public.claim_reward(text, int),
  public.ad_reward(), public.place_bet(text, int, int), public.report_result(text, int), public.refund_stale_bets()
  to authenticated;
