// Starts a Stripe Checkout session for a diamond pack and returns its URL.
// Needs secrets: STRIPE_SECRET_KEY, SITE_URL (set with `supabase secrets set`).
import Stripe from "npm:stripe@17.7.0";
import { createClient } from "npm:@supabase/supabase-js@2.49.4";

const PACKS: Record<string, { diamonds: number; cents: number; name: string }> = {
  small: { diamonds: 100, cents: 99, name: "100 Diamonds" },
  medium: { diamonds: 550, cents: 499, name: "550 Diamonds" },
  large: { diamonds: 1200, cents: 999, name: "1200 Diamonds" },
};

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  const key = Deno.env.get("STRIPE_SECRET_KEY");
  if (!key) return Response.json({ error: "Store not configured yet" }, { status: 503, headers: cors });

  const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } },
  });
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Sign in first" }, { status: 401, headers: cors });

  const { pack } = await req.json();
  const p = PACKS[pack];
  if (!p) return Response.json({ error: "Unknown pack" }, { status: 400, headers: cors });

  const stripe = new Stripe(key);
  const site = Deno.env.get("SITE_URL") ?? "http://localhost:3000";
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ quantity: 1, price_data: { currency: "usd", unit_amount: p.cents, product_data: { name: p.name } } }],
    metadata: { user_id: user.id, diamonds: String(p.diamonds) },
    success_url: `${site}/?purchase=success`,
    cancel_url: `${site}/?purchase=cancel`,
  });
  return Response.json({ url: session.url }, { headers: cors });
});
