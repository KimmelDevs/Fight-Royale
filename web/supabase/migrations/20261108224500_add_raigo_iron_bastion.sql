-- RAIGO_IRON_BASTION_V1: review after existing migrations; do not apply automatically.
-- Extends the character validation list WITHOUT removing existing roster entries.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT c = ANY (ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','volta','sylva',
    'nyx','rook','gale','bob','kira','raven','ash','veyr','zarek','kaizen',
    'nesa','roxy','zenith','nythera','zephyr','raigo','leon','sakura','yuki','bruno'
  ]);
$$;
CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
  SELECT ARRAY[
    'aster','vesper','garrick','kaede','ember','marina','nyx','rook','gale',
    'bob','kira','raven','ash','veyr','zarek','kaizen','nesa','roxy',
    'zenith','nythera','zephyr','raigo'
  ]::text[];
$$;
