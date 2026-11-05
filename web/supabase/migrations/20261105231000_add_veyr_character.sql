-- Allow Veyr purchases and loadouts for signed-in players.
-- Includes current roster AND older catalog IDs to avoid invalidating legacy purchases.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash','veyr',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;
