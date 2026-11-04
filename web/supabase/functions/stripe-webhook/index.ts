// Credits diamonds when Stripe reports a completed checkout. Idempotent per session.
// Needs secrets: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET. Deploy with --no-verify-jwt
// (Stripe calls it without a Supabase token; the Stripe signature is the authentication).
import Stripe from "npm:stripe@17.7.0";
import { createClient } from "npm:@supabase/supabase-js@2.49.4";

Deno.serve(async (req) => {
  const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!);
  const sig = req.headers.get("stripe-signature") ?? "";
  const body = await req.text();
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, sig, Deno.env.get("STRIPE_WEBHOOK_SECRET")!);
  } catch {
    return new Response("bad signature", { status: 400 });
  }
  if (event.type === "checkout.session.completed") {
    const s = event.data.object as Stripe.Checkout.Session;
    if (s.payment_status === "paid" && s.metadata?.user_id) {
      const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
      const { error } = await admin.rpc("credit_purchase", {
        p_session: s.id, p_user: s.metadata.user_id, p_diamonds: Number(s.metadata.diamonds),
      });
      if (error) return new Response(error.message, { status: 500 });
    }
  }
  return new Response("ok");
});
