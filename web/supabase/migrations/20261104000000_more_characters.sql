-- New fighters: Leon, Sakura, Raven, Yuki, Bruno and Ash become unlockable.
create or replace function public.valid_character(c text) returns boolean language sql immutable as $$
  select c = any (array['aster','vesper','garrick','kaede','ember','marina','volta','sylva','nyx','rook','kira',
                        'leon','sakura','raven','yuki','bruno','ash'])
$$;
