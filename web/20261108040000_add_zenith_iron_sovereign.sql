-- Zenith — The Iron Sovereign. Apply after the Roxy migration (if installed).
-- This mirrors the character lists from the shipped Roxy migration, plus Zenith.
-- If you have extra custom character IDs, add them to BOTH lists before applying.
CREATE OR REPLACE FUNCTION public.valid_character(c text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT c = ANY (ARRAY[
   'aster','vesper','garrick','kaede','ember','marina',
   'nyx','rook','gale','bob','kira','raven','ash',
   'veyr','zarek','kaizen','nesa','roxy','zenith',
   'volta','sylva','leon','sakura','yuki','bruno'
 ])
$$;

CREATE OR REPLACE FUNCTION public.all_characters()
RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
 SELECT ARRAY[
   'aster','vesper','garrick','kaede','ember','marina',
   'nyx','rook','gale','bob','kira','raven','ash',
   'veyr','zarek','kaizen','nesa','roxy','zenith'
 ]::text[]
$$;
