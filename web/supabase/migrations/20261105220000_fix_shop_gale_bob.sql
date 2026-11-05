-- Align Supabase's purchasable fighter catalog with src/game/roster.ts.
-- Fixes signed-in purchases of Gale and Bob failing with "unknown character".
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT c = ANY(ARRAY[
    'aster', 'vesper', 'garrick', 'kaede',
    'ember', 'marina', 'nyx', 'rook',
    'kira', 'raven', 'ash', 'gale', 'bob'
  ])
$$;
