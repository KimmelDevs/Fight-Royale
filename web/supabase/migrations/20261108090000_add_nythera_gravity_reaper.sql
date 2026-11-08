-- NYTHERA_GRAVITY_REAPER_INSTALL_V1 -- optional; apply with `npx supabase db push`.
-- Merge any custom character IDs into these allowlists before applying.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy','zenith','nythera',
    'volta','sylva','leon','sakura','yuki','bruno'
  ])
$$;
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash',
    'veyr','zarek','kaizen','nesa','roxy','zenith','nythera'
  ]::text[]
$$;
