import { handleCors } from "../lib/http.js";
import { getDb } from "../lib/db.js";

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const blogBaseUrl =
    process.env.BLOG_BASE_URL || "https://hotspot.edgesoft.org";

  function redirect(status: string) {
    return new Response(null, {
      status: 302,
      headers: { Location: `${blogBaseUrl}/verify.html?status=${status}` },
    });
  }

  try {
    const url = new URL(request.url);
    const token = url.searchParams.get("token");

    if (!token) return redirect("invalid");

    const db = getDb();
    const result = await db.execute({
      sql: "SELECT id, verified, email FROM subscribers WHERE verification_token = ?",
      args: [token],
    });

    if (result.rows.length === 0) return redirect("invalid");

    const subscriber = result.rows[0] as unknown as {
      id: number;
      verified: number;
      email: string;
    };

    if (subscriber.verified) return redirect("already");

    await db.execute({
      sql: "UPDATE subscribers SET verified = 1, verified_at = datetime('now') WHERE id = ? AND verified = 0",
      args: [subscriber.id],
    });

    return redirect("success");
  } catch (err) {
    console.error(`[VerifyController] Error: ${err}`);
    return redirect("error");
  }
}
