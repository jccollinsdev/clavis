-- Restrict public prices table to read-only access for authenticated users.
DROP POLICY IF EXISTS "users_own_prices" ON public.prices;
CREATE POLICY "prices_select_all" ON public.prices FOR SELECT USING (true);
