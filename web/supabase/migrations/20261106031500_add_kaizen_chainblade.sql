-- Kaizen — Chainblade Berserker
-- Run in Supabase SQL Editor after previous roster migrations.
-- This updates the signed-in shop's valid-character allowlist.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;
