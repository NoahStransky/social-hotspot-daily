import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { isValidEmail } from "../_lib";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const email = (searchParams.get("email") || "").trim().toLowerCase();

    if (!email || !isValidEmail(email)) {
      return NextResponse.redirect(new URL("/unsubscribe?status=invalid", request.url));
    }

    const db = getDb();
    const result = await db.execute({
      sql: "UPDATE subscribers SET unsubscribed = 1 WHERE email = ?",
      args: [email],
    });

    if (result.rowsAffected === 0) {
      return NextResponse.redirect(new URL("/unsubscribe?status=notfound", request.url));
    }

    return NextResponse.redirect(new URL("/unsubscribe?status=success", request.url));
  } catch (err) {
    console.error(`[Unsubscribe] Error: ${err}`);
    return NextResponse.redirect(new URL("/unsubscribe?status=invalid", request.url));
  }
}
