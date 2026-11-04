-- Starting fighters are now Aster, Ember and Garrick. New accounts get them by default;
-- existing accounts keep everything they own and also get Garrick.
alter table public.profiles alter column characters set default array['aster', 'ember', 'garrick'];
update public.profiles set characters = array_append(characters, 'garrick') where not ('garrick' = any (characters));
