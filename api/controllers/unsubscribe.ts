import { handleCors } from "../lib/http.js";
import { getDb } from "../lib/db.js";
import { isValidEmail } from "../lib/token.js";

export async function GET(request: Request): Promise<Response> {
  const cors = handleCors(request);
  if (cors) return cors;

  const blogBaseUrl =
    process.env.BLOG_BASE_URL || "https://hotspot.edgesoft.org";

  function redirect(status: string) {
    return new Response(null, {
      status: 302,
      headers: { Location: `${blogBaseUrl}/unsubscribe.html?status=${status}` },
    });
  }

  try {
    const url = new URL(request.url);
    const email = (url.searchParams.get("email") || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) return redirect("invalid");

    const db = getDb();
    const result = await db.execute({
      sql: "UPDATE subscribers SET unsubscribed = 1 WHERE email = ?",
      args: [email],
    });

    if ((result.rowsAffected || 0) === 0) return redirect("notfound");

    return redirect("success");
  } catch (err) {
    console.error(`[UnsubscribeController] Error: ${err}`);
    return redirect("error");
  }
}
