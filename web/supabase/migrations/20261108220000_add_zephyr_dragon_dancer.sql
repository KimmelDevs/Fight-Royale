-- Zephyr / Dragon Dancer. Extends the installed allowlist without deleting its other IDs.
-- Review and apply this migration using your existing Supabase workflow.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','volta','sylva',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr','leon','sakura','yuki','bruno'
  ]);
$$;

-- Include Zephyr in the admin roster. Ownership of other fighters stays unchanged.
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr'
  ]::text[]
$$;
