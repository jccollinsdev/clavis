import "jsr:@supabase/functions-js/edge-runtime.d.ts";

Deno.serve(async (req: Request) => {
  const { token } = await req.json();

  if (!token || typeof token !== "string") {
    return new Response(JSON.stringify({ error: "Invalid token" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) {
    return new Response(JSON.stringify({ error: "Missing Authorization header" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  const userResponse = await fetch(`${supabaseUrl}/auth/v1/user`, {
    headers: {
      Authorization: authHeader,
      apikey: supabaseKey,
    },
  });

  if (!userResponse.ok) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const user = await userResponse.json();
  const userId = user.id;

  const upsertResponse = await fetch(`${supabaseUrl}/rest/v1/user_preferences`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${supabaseKey}`,
      apikey: supabaseKey,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
      "Upsert": "true",
    },
    body: JSON.stringify({
      user_id: userId,
      apns_token: token,
      updated_at: new Date().toISOString(),
    }),
  });

  if (!upsertResponse.ok) {
    return new Response(JSON.stringify({ error: "Failed to save token" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ success: true }), {
    headers: { "Content-Type": "application/json" },
  });
});
