-- ROXY_SNOW_PUPPET_MASTER_V1
-- Register Roxy with the signed-in shop and migrate ownership from an older Niva install.
-- Apply AFTER the existing character migrations. Keep this as a NEW migration file.
-- If you have other custom fighter IDs, add them to BOTH arrays before applying.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;

-- Admins automatically receive Roxy too, alongside all currently playable fighters.
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy'
  ]::text[]
$$;

-- Preserve prior Niva purchases (if the older installer was already used).
UPDATE public.profiles
SET characters = array_replace(characters, 'niva', 'roxy'),
    skills = array_replace(skills, 'niva', 'roxy'),
    loadouts = CASE
      WHEN loadouts ? 'niva'
      THEN (loadouts - 'niva') || jsonb_build_object('roxy', loadouts -> 'niva')
      ELSE loadouts
    END
WHERE 'niva' = ANY(characters)
   OR 'niva' = ANY(skills)
   OR loadouts ? 'niva';
