import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders })
  }

  try {
    // ============================
    // 1. Lecture paramètres
    // ============================
    const body = await req.json().catch(() => ({}))
    const account_id = body.account_id ?? 4
    const environment = body.environment

    // ============================
    // 2. Init Supabase
    // ============================
    const supabaseUrl =
      Deno.env.get("SUPABASE_URL") ??
      Deno.env.get("SUPABASE_PROJECT_REF")?.replace(/^(.+)$/, "https://$1.supabase.co")

    const supabaseKey =
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ??
      Deno.env.get("SUPABASE_ANON_KEY")

    if (!supabaseUrl || !supabaseKey) {
      return jsonError("Supabase env vars manquantes", 500)
    }

    const supabase = createClient(supabaseUrl, supabaseKey)

    // ============================
    // 3. Récupération credentials
    // ============================
    const { data: account, error: dbError } = await supabase
      .from("trading_brokeraccount")
      .select(`
        id,
        name,
        broker_type,
        saxo_refresh_token,
        saxo_client_id,
        saxo_client_secret,
        saxo_environment
      `)
      .eq("id", account_id)
      .eq("broker_type", "SAXO")
      .single()

    if (dbError || !account) {
      return jsonError("Compte SAXO introuvable", 404, dbError)
    }

    if (!account.saxo_refresh_token || !account.saxo_client_id || !account.saxo_client_secret) {
      return jsonError("Credentials Saxo incomplets", 400)
    }

    // ============================
    // 4. Détermination environnement
    // ============================
    const env =
      environment ??
      (account.saxo_environment === "live" ? "live" : "sim")

    const authUrl =
      env === "live"
        ? "https://live.logonvalidation.net/token"
        : "https://sim.logonvalidation.net/token"

    console.log("Saxo refresh", {
      account_id,
      env,
      authUrl,
      client_id: account.saxo_client_id.slice(0, 6) + "...",
    })

    // ============================
    // 5. Appel API Saxo
    // ============================
    const formData = new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: account.saxo_refresh_token,
      client_id: account.saxo_client_id,
      client_secret: account.saxo_client_secret,
    })

    const response = await fetch(authUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    })

    const rawText = await response.text()

    // ============================
    // 6. Parsing sécurisé
    // ============================
    let tokenData: any
    try {
      tokenData = JSON.parse(rawText)
    } catch {
      console.error("Saxo non JSON:", rawText)
      return jsonError("Réponse Saxo non JSON", 502, {
        http_status: response.status,
        raw_response: rawText.substring(0, 800),
      })
    }

    if (!response.ok) {
      return jsonError(
        tokenData.error_description || tokenData.error || "Erreur Saxo",
        response.status,
        tokenData
      )
    }

    // ============================
    // 7. Mise à jour DB
    // ============================
    const expiresIn = tokenData.expires_in ?? 3600
    const expiresAt = new Date(Date.now() + expiresIn * 1000).toISOString()

    const updateData: any = {
      saxo_access_token: tokenData.access_token,
      saxo_token_expires_at: expiresAt,
    }

    if (tokenData.refresh_token) {
      updateData.saxo_refresh_token = tokenData.refresh_token
    }

    const { error: updateError } = await supabase
      .from("trading_brokeraccount")
      .update(updateData)
      .eq("id", account_id)

    if (updateError) {
      console.error("DB update error:", updateError)
    }

    // ============================
    // 8. Réponse OK
    // ============================
    return new Response(
      JSON.stringify({
        success: true,
        account_id,
        account_name: account.name,
        environment: env,
        access_token: tokenData.access_token,
        refresh_token: tokenData.refresh_token ?? account.saxo_refresh_token,
        expires_in: expiresIn,
        expires_at: expiresAt,
        token_type: tokenData.token_type ?? "Bearer",
        updated_in_db: !updateError,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    )
  } catch (error) {
    console.error("Erreur globale:", error)
    return jsonError(error.message ?? "Erreur inconnue", 500)
  }
})

// ============================
// Helpers
// ============================
function jsonError(message: string, status = 500, details?: any) {
  return new Response(
    JSON.stringify({
      success: false,
      error: message,
      details,
    }),
    {
      status,
      headers: {
        ...corsHeaders,
        "Content-Type": "application/json",
      },
    }
  )
}
