import { createClient } from "@libsql/client";

let _db: ReturnType<typeof createClient> | null = null;

export function getDb() {
  if (!_db) {
    _db = createClient({
      url: process.env.TURSO_DATABASE_URL!,
      authToken: process.env.TURSO_AUTH_TOKEN!,
    });
  }
  return _db;
}

export interface SubscriberRow {
  id: number;
  email: string;
  verified: number;
  verification_token: string | null;
  created_at: string;
  verified_at: string | null;
  unsubscribed: number;
  preferences: string;
}
