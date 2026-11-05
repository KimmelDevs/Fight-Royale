-- Zarek — Storm Glaive. Run after your previous roster migrations.
-- The character shop uses public.valid_character() as its allowlist.
-- Keep the current roster IDs and the legacy IDs from the Veyr migration.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;
