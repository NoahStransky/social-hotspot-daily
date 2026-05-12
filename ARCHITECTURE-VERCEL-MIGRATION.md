# Architecture Plan: Migrate Subscription System from Cloudflare Worker to Vercel + Turso

> **Project**: social-hotspot-daily
> **Date**: 2026-05-12
> **Status**: Design Document

---

## Table of Contents

1. [Overview](#1-overview)
2. [Directory Structure](#2-directory-structure)
3. [Vercel API Design](#3-vercel-api-design)
4. [Turso Database Schema](#4-turso-database-schema)
5. [Turnstile Integration](#5-turnstile-integration)
6. [Environment Variables](#6-environment-variables)
7. [DNS Changes](#7-dns-changes)
8. [Deletion Checklist](#8-deletion-checklist)
9. [Implementation Tasks](#9-implementation-tasks)

---

## 1. Overview

### Current State

| Component | Current | Target |
|---|---|---|
| API Backend | Cloudflare Worker (TypeScript, D1) | Vercel Serverless Functions (TypeScript, Turso) |
| Database | Cloudflare D1 (SQLite-compatible) | Turso (serverless SQLite) |
| Static Site | GitHub Pages (docs/) | GitHub Pages (docs/) — **no change** |
| Email | Resend API | Resend API — **no change** |
| Bot Detection | None | Cloudflare Turnstile (free) |
| DNS | Cloudflare | Cloudflare — **keep** |
| Daily Content | GitHub Actions | GitHub Actions — **no change** |

### Key Principles

- **Minimal HTML changes**: The existing docs/ HTML files already have placeholder JS. We update API URLs and add Turnstile.
- **Compatible D1 → Turso migration**: Both use SQLite-compatible SQL. The D1 `datetime('now')` becomes Turso's `datetime('now')` or `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`.
- **Hobby plan compatible**: Vercel Hobby = 60 serverless invocations per day (more than enough), 10s timeout (fine for API calls), 100MB response size.
- **Vercel automatically routes** `api/*.ts` files to `https://domain/api/*`.

---

## 2. Directory Structure

```
social-hotspot-daily/
├── api/                          # NEW — Vercel Serverless Functions
│   ├── subscribe.ts              #   POST /api/subscribe
│   ├── verify.ts                 #   GET  /api/verify?token=xxx
│   ├── unsubscribe.ts            #   GET  /api/unsubscribe?email=xxx
│   ├── resend-verify.ts          #   POST /api/resend-verify
│   ├── status.ts                 #   GET  /api/status?email=xxx
│   ├── health.ts                 #   GET  /api/health
│   ├── subscribers.ts            #   GET  /api/subscribers (authenticated)
│   └── _lib/                     #   Shared library
│       ├── db.ts                 #     Turso client connection
│       ├── email.ts              #     Resend email helpers (copied from Worker)
│       ├── token.ts              #     Token generation + validation
│       ├── turnstile.ts          #     Turnstile verification helper
│       └── cors.ts               #     CORS headers
├── cloudflare-worker/            # DELETE — entire directory after migration
│   ├── wrangler.toml
│   └── src/
│       └── index.ts
├── docs/                         # KEEP — static site (minor updates)
│   ├── subscribe.html            # UPDATE — API URL + add Turnstile
│   ├── verify.html               # UPDATE — fetch verification from API
│   └── unsubscribe.html          # UPDATE — fetch unsubscription from API
├── newsletter/
│   ├── db.py                     # KEEP — local SQLite fallback (no change)
│   └── mailer.py                 # NO CHANGE — already has WORKER_SUBSCRIBERS_API fallback
├── .github/workflows/
│   └── daily.yml                 # UPDATE — WORKER_SUBSCRIBERS_API → VERCEL_SUBSCRIBERS_API
├── vercel.json                   # NEW — Vercel configuration
├── package.json                  # NEW — Node.js deps
├── tsconfig.json                 # NEW — TypeScript config
└── .env.example                  # NEW — Environment variable reference
```

---

## 3. Vercel API Design

### 3.1 Shared Library: `api/_lib/db.ts`

```typescript
import { createClient } from "@libsql/client";

export function getDb() {
  return createClient({
    url: process.env.TURSO_DATABASE_URL!,
    authToken: process.env.TURSO_AUTH_TOKEN!,
  });
}
```

### 3.2 Shared Library: `api/_lib/cors.ts`

```typescript
const ALLOWED_ORIGINS = [
  "https://hotspot.edgesoft.org",
  "https://noahstransky.github.io",
  "http://localhost:8787",
  "http://localhost:8788",
  "http://127.0.0.1:8787",
  "http://127.0.0.1:8788",
];

export function corsHeaders(origin: string | null): Record<string, string> {
  const allowed = origin && ALLOWED_ORIGINS.includes(origin)
    ? origin
    : "https://noahstransky.github.io";
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
  };
}

export function jsonResponse(data: unknown, status = 200, cors: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...cors },
  });
}
```

### 3.3 Shared Library: `api/_lib/token.ts`

```typescript
import crypto from "node:crypto";

export function generateToken(): string {
  return crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
}

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim().toLowerCase());
}
```

### 3.4 Shared Library: `api/_lib/email.ts`

Direct copy of the `sendVerificationEmail` function from the current Worker, but using `process.env` instead of `env.XXX`. Same Resend API call.

### 3.5 Shared Library: `api/_lib/turnstile.ts`

```typescript
export async function verifyTurnstileToken(token: string): Promise<boolean> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) return false;

  try {
    const resp = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret, response: token }),
    });
    const data = await resp.json();
    return data.success === true;
  } catch {
    return false;
  }
}
```

### 3.6 Endpoint: `POST /api/subscribe` → `api/subscribe.ts`

**Request:**
```json
{ "email": "user@example.com", "turnstile_token": "0.xxx..." }
```

**Logic flow:**
1. Parse body, validate email
2. **Verify Turnstile token** — reject with `{ error: "Bot detected" }` on failure
3. Check if subscriber exists in Turso
4. If exists & verified & not unsubscribed → 409 `already subscribed`
5. If exists & unsubscribed → re-activate, generate new token, send verification → 200
6. If exists & not verified → resend with existing/new token → 200
7. If new → INSERT, send verification → 201

**Responses:**
- 201: `{ message: "...", email: "..." }`
- 200: `{ message: "...", email: "..." }` (resend/re-subscribe)
- 400: `{ error: "Invalid email address." }`
- 409: `{ error: "This email is already subscribed and verified." }`
- 500: `{ error: "Failed to send verification email..." }` or `{ error: "Internal server error." }`

**Database queries:**
- SELECT: `SELECT id, verified, unsubscribed, verification_token FROM subscribers WHERE email = ?`
- INSERT: `INSERT INTO subscribers (email, verification_token) VALUES (?, ?)`
- UPDATE re-activate: `UPDATE subscribers SET unsubscribed = 0, verified = 0, verification_token = ?, verified_at = NULL WHERE email = ?`
- UPDATE new token: `UPDATE subscribers SET verification_token = ? WHERE email = ?`

### 3.7 Endpoint: `GET /api/verify?token=xxx` → `api/verify.ts`

**Request:** Query param `?token=xxx`

**Logic flow:**
1. Read `token` from query params
2. If missing → redirect to `/verify.html?status=invalid`
3. Look up subscriber by token in Turso
4. If not found → redirect `/verify.html?status=invalid`
5. If already verified → redirect `/verify.html?status=already`
6. Otherwise → UPDATE verified=1, redirect `/verify.html?status=success`

**Response:** Always a 302 redirect to the static HTML page.

**Database query:**
- SELECT: `SELECT id, verified, email FROM subscribers WHERE verification_token = ?`
- UPDATE: `UPDATE subscribers SET verified = 1, verified_at = datetime('now') WHERE id = ? AND verified = 0`

### 3.8 Endpoint: `GET /api/unsubscribe?email=xxx` → `api/unsubscribe.ts`

**Request:** Query param `?email=xxx`

**Logic flow:**
1. Read and validate email
2. UPDATE unsubscribed=1
3. Check affected rows — 0 means not found
4. Redirect with status

**Response:** 302 redirect to `/unsubscribe.html?status=success|notfound|invalid|error`

**Database query:**
- `UPDATE subscribers SET unsubscribed = 1 WHERE email = ?`
- Check: Turso libSQL client returns `result.rowsAffected` (not `result.meta.changes`)

### 3.9 Endpoint: `POST /api/resend-verify` → `api/resend-verify.ts`

**Request:** `{ "email": "..." }`

**Logic flow:** Identical to existing Worker logic — lookup, check verified status, generate token if missing, send email.

**Note:** This endpoint may also need Turnstile verification to prevent abuse. Consider adding it.

### 3.10 Endpoint: `GET /api/status?email=xxx` → `api/status.ts`

**Request:** Query param `?email=xxx`

**Logic flow:** Lookup subscriber, return status string `verified|pending_verification|unsubscribed|not_found`.

**Database query:**
- `SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE email = ?`

### 3.11 Endpoint: `GET /api/health` → `api/health.ts`

**Logic:** Execute `SELECT 1 as ok`, return `{ ok: true }` or `{ ok: false, error: "..." }` with 503.

### 3.12 Endpoint: `GET /api/subscribers` → `api/subscribers.ts` (Authenticated)

**Authentication:**
- Check `Authorization: Bearer <SUBSCRIBERS_API_KEY>` header
- Reject 401 if missing or wrong

**Logic:** Return all verified + active subscribers as JSON array.

**Database query:**
- `SELECT email, verified, unsubscribed, created_at, verified_at FROM subscribers WHERE verified = 1 AND unsubscribed = 0 ORDER BY created_at DESC`

**Response:**
```json
{ "subscribers": [...], "count": 42 }
```

### 3.13 Vercel Configuration: `vercel.json`

```json
{
  "functions": {
    "api/*.ts": {
      "maxDuration": 10
    }
  }
}
```

### 3.14 CORS Preflight Handling

Vercel does not have built-in OPTIONS handling. Each endpoint file must handle OPTIONS requests. The simplest pattern (Vercel-recommended):

```typescript
// At top of each POST endpoint:
if (request.method === "OPTIONS") {
  return new Response(null, { status: 204, headers: corsHeaders(request.headers.get("origin")) });
}
```

---

## 4. Turso Database Schema

### 4.1 Create Database

```bash
# Via Turso CLI
turso db create social-hotspot-subscribe-db
turso db show social-hotspot-subscribe-db --url
turso db create-token social-hotspot-subscribe-db
```

### 4.2 Schema (Compatible with existing D1)

```sql
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    verified INTEGER DEFAULT 0,       -- D1 uses 0/1 for booleans
    verification_token TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    verified_at TEXT,
    unsubscribed INTEGER DEFAULT 0,    -- D1 uses 0/1 for booleans
    preferences TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS send_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    sent_at TEXT DEFAULT (datetime('now')),
    status TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_verified ON subscribers(verified);
CREATE INDEX IF NOT EXISTS idx_subscribers_token ON subscribers(verification_token);
```

**Migration note:** `datetime('now')` works identically in both D1 (SQLite) and Turso (libSQL). No schema changes needed.

### 4.3 Data Migration from D1

```bash
# 1. Export from D1
wrangler d1 execute social-hotspot-subscribe-db \
  --command "SELECT * FROM subscribers" \
  --json > d1_subscribers.json

wrangler d1 execute social-hotspot-subscribe-db \
  --command "SELECT * FROM send_log" \
  --json > d1_send_log.json

# 2. Import to Turso via SQL
turso db shell social-hotspot-subscribe-db < import.sql
```

Where `import.sql` contains INSERT statements built from the exported JSON.

**Alternative:** Use a small migration script that reads D1 exports and writes SQL for Turso.

### 4.4 Turso → libSQL Client Differences from D1

| D1 API | Turso/libSQL API | Notes |
|---|---|---|
| `env.DB.prepare(sql).bind(...)` | `db.execute({ sql, args: [...] })` | Different syntax |
| `.first<T>()` | `rows[0] as T` | Manual array access |
| `.run()` | `db.execute(...)` | Returns `{ rowsAffected, rows }` |
| `.all()` | `db.execute(...)` | Returns `{ rows, columns }` |
| `result.meta.changes` | `result.rowsAffected` | Property name differs |

---

## 5. Turnstile Integration

### 5.1 Overview

Cloudflare Turnstile is a free CAPTCHA alternative that works independently of Cloudflare Workers. It uses the same Cloudflare API but can be embedded on any site and verified by any backend.

### 5.2 Setup Steps

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → Turnstile → Add a widget
2. Create a widget key: `0x4AAAA...` (site key)
3. Get the secret key for server-side verification
4. Add both to Vercel env vars (see Section 6)

### 5.3 Frontend: Updates to `docs/subscribe.html`

**Add Turnstile script tag in `<head>`:**
```html
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
```

**Add Turnstile widget inside the form, after the email input:**
```html
<div class="cf-turnstile" data-sitekey="0x4AAAA...YOUR_SITE_KEY" data-theme="dark" data-callback="onTurnstileSuccess"></div>
```

**Update the JavaScript:**
```javascript
let turnstileToken = "";

function onTurnstileSuccess(token) {
  turnstileToken = token;
}

document.getElementById('subscribeForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const email = document.getElementById('email').value;
  const btn = document.getElementById('submitBtn');
  const msg = document.getElementById('message');

  if (!turnstileToken) {
    msg.className = 'message error';
    msg.textContent = 'Please complete the bot verification.';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Processing...';

  try {
    const resp = await fetch('https://hotspot.edgesoft.org/api/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, turnstile_token: turnstileToken }),
    });
    const data = await resp.json();

    if (resp.ok) {
      msg.className = 'message success';
      msg.innerHTML = `<strong>${data.message}</strong>`;
      btn.textContent = 'Subscribed ✓';
    } else {
      msg.className = 'message error';
      msg.textContent = data.error || 'Something went wrong.';
      btn.disabled = false;
      btn.textContent = 'Subscribe';
      turnstile.reset();
      turnstileToken = "";
    }
  } catch (err) {
    msg.className = 'message error';
    msg.textContent = 'Network error. Please try again.';
    btn.disabled = false;
    btn.textContent = 'Subscribe';
  }
});
```

**Styling for Turnstile (light-colored overlay on dark background):**
```css
.cf-turnstile {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}
.cf-turnstile iframe {
  /* Force dark theme if data-theme="dark" doesn't work everywhere */
}
```

### 5.4 Backend: Verification in `api/subscribe.ts`

```typescript
import { verifyTurnstileToken } from "./_lib/turnstile";

export async function POST(request: Request) {
  const cors = corsHeaders(request.headers.get("origin"));

  // Handle preflight
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors });
  }

  const body = await request.json();
  const { email, turnstile_token } = body;

  // Validate Turnstile
  if (!turnstile_token || !(await verifyTurnstileToken(turnstile_token))) {
    return jsonResponse({ error: "Verification failed. Please try again." }, 403, cors);
  }

  // ... rest of subscribe logic unchanged
}
```

---

## 6. Environment Variables

### 6.1 Vercel Project Environment Variables

| Variable | Description | Source | Secret |
|---|---|---|---|
| `TURSO_DATABASE_URL` | Turso database URL (from `turso db show`) | Turso CLI | No |
| `TURSO_AUTH_TOKEN` | Turso auth token (from `turso db create-token`) | Turso CLI | **Yes** |
| `RESEND_API_KEY` | Resend API key (same as current) | Resend Dashboard | **Yes** |
| `SUBSCRIBERS_API_KEY` | API key for GitHub Actions auth (same as current) | Generate new or reuse | **Yes** |
| `BLOG_BASE_URL` | Base URL of the site (e.g., `https://hotspot.edgesoft.org`) | Yours | No |
| `FROM_EMAIL` | Sender email address (e.g., `newsletter@edgesoft.org`) | Yours | No |
| `TURNSTILE_SITE_KEY` | Turnstile site key ("0x4AAAA...") | Cloudflare Turnstile | No |
| `TURNSTILE_SECRET_KEY` | Turnstile secret key | Cloudflare Turnstile | **Yes** |

### 6.2 GitHub Actions Variables (Update from Current)

| Current Variable | New Variable | Change |
|---|---|---|
| `WORKER_SUBSCRIBERS_API` | `WORKER_SUBSCRIBERS_API` (keep name) | Update URL value only |
| `WORKER_API_KEY` | `WORKER_API_KEY` (keep name) | Reuse or regen key |

The URL changes from `https://hotspot.edgesoft.org/api/subscribers` (Worker) to `https://hotspot.edgesoft.org/api/subscribers` (Vercel) — **the path stays the same** if routing is configured identically. Only if a Worker-specific subdomain was used does the URL change.

---

## 7. DNS Changes

### 7.1 Current Setup

- Domain: `hotspot.edgesoft.org`
- DNS hosted at Cloudflare
- Currently: Cloudflare Worker handles `hotspot.edgesoft.org/api/*` via Worker Routes
- Static files: GitHub Pages via `noahstransky.github.io`

### 7.2 Required Changes

**Add a CNAME record** pointing to Vercel's deployment:

| Type | Name | Target | Proxy Status |
|---|---|---|---|
| CNAME | `api` | `cname.vercel-dns.com` | DNS Only (grey cloud) |

Wait — actually, **Vercel needs the apex domain or a subdomain to handle `hotspot.edgesoft.org/api/*`**. There are two approaches:

**Approach A: Vercel handles all domain traffic via a CNAME on the apex (Recommended)**
1. In Cloudflare DNS: Change the `hotspot` A/AAAA records or apex `@` to point to Vercel
   - Type: CNAME (if using Cloudflare's CNAME flattening / proxied)
   - Name: `hotspot` (or `@`)
   - Target: `cname.vercel-dns.com`
   - Proxy: Proxied (orange cloud) — so Cloudflare still handles DNS, DDoS, and Turnstile
2. In Vercel: Add `hotspot.edgesoft.org` as a custom domain in the project settings
3. Vercel auto-provisions SSL certs via Let's Encrypt

⚠️ **Important**: The domain `hotspot.edgesoft.org` currently resolves to GitHub Pages. Changing it to Vercel means **Vercel needs to serve the static files too**, OR we keep GitHub Pages for static and use a subdomain for the API.

**Approach B: Subdomain for API only (Recommended for minimal disruption)**
1. Add CNAME: `api.hotspot` → `cname.vercel-dns.com` (or the Vercel deployment URL)
2. Vercel project domain: `api.hotspot.edgesoft.org`
3. Vercel serves API at `https://api.hotspot.edgesoft.org/api/*`
4. GitHub Pages continues serving `https://hotspot.edgesoft.org` unchanged
5. Update subscribe.html to POST to `https://api.hotspot.edgesoft.org/api/subscribe`

**Approach C: Vercel rewrites (if domain stays at Vercel)**
- Vercel can rewrite `api/*` paths even if the apex domain is pointed to Vercel
- But this requires the apex domain to be at Vercel, not GitHub Pages

### 7.3 Recommendation

**Use Approach B** (subdomain for API). Minimal DNS change, no risk to the existing static site.

| Record | Type | Name | Target | Proxy |
|---|---|---|---|---|
| Existing | A/AAAA/CNAME | `hotspot` | GitHub Pages | Proxied |
| NEW | CNAME | `api` | `cname.vercel-dns.com` | Proxied (orange cloud) |

Then in Vercel:
- Project: `social-hotspot-daily`
- Domains: add `api.hotspot.edgesoft.org`
- Auto SSL: enabled by default

---

## 8. Deletion Checklist

After migration is verified working:

- [ ] **Delete Cloudflare Worker**: `wrangler delete social-hotspot-subscribe`
- [ ] **Delete Cloudflare D1 database**: `wrangler d1 delete social-hotspot-subscribe-db`
- [ ] **Remove Worker Routes** in Cloudflare Dashboard (zone → Workers → Routes)
- [ ] **Remove Worker env/secrets** (RESEND_API_KEY, SUBSCRIBERS_API_KEY — no longer in Cloudflare)
- [ ] **Delete directory**: `rm -rf cloudflare-worker/`
- [ ] **Update daily.yml**: Remove any Cloudflare-specific env references if no longer needed
- [ ] **Update package.json**: Remove any Cloudflare devDependencies (`wrangler`, `@cloudflare/workers-types`)

---

## 9. Implementation Tasks

### Phase 1: Foundation (1-2 hours)

| # | Task | Files | Details |
|---|---|---|---|
| 1.1 | Create `package.json` | `package.json` | Dependencies: `@libsql/client`, `@types/node`, `typescript` |
| 1.2 | Create `tsconfig.json` | `tsconfig.json` | Target ES2022, module NodeNext, strict mode |
| 1.3 | Create `vercel.json` | `vercel.json` | Basic config with `maxDuration: 10` |
| 1.4 | Create `api/_lib/` shared modules | `db.ts`, `cors.ts`, `token.ts`, `email.ts`, `turnstile.ts` | See Section 3 |
| 1.5 | Create Turso database | (Turso CLI) | `turso db create`, save URL + token |

### Phase 2: API Endpoints (2-3 hours)

| # | Task | Files | Details |
|---|---|---|---|
| 2.1 | Implement `POST /api/subscribe` | `api/subscribe.ts` | Full subscribe flow + Turnstile verification |
| 2.2 | Implement `GET /api/verify` | `api/verify.ts` | Token lookup + redirect |
| 2.3 | Implement `GET /api/unsubscribe` | `api/unsubscribe.ts` | Email lookup + redirect |
| 2.4 | Implement `POST /api/resend-verify` | `api/resend-verify.ts` | Resend verification email |
| 2.5 | Implement `GET /api/status` | `api/status.ts` | Status check |
| 2.6 | Implement `GET /api/health` | `api/health.ts` | Database health check |
| 2.7 | Implement `GET /api/subscribers` | `api/subscribers.ts` | Authenticated subscriber list |

### Phase 3: Frontend Updates (1 hour)

| # | Task | Files | Details |
|---|---|---|---|
| 3.1 | Update `subscribe.html` | `docs/subscribe.html` | Add Turnstile widget, update API endpoint to Vercel URL, rewrite JS to fetch API |
| 3.2 | Update `verify.html` | `docs/verify.html` | Update to use query params from redirect (already works — verify.ts redirects with `?status=xxx`) |
| 3.3 | Update `unsubscribe.html` | `docs/unsubscribe.html` | Update to use query params from redirect (already works — same as verify) |

### Phase 4: Configuration & Deployment (1 hour)

| # | Task | Files | Details |
|---|---|---|---|
| 4.1 | Set up Vercel project | Vercel Dashboard | Connect GitHub repo, configure env vars |
| 4.2 | Configure DNS | Cloudflare Dashboard | Add CNAME for `api` subdomain |
| 4.3 | Configure Turnstile | Cloudflare Dashboard | Create widget, get keys, add to Vercel env |
| 4.4 | Deploy Vercel | — | `vercel --prod` or auto-deploy from GitHub |
| 4.5 | Test all endpoints | — | curl each endpoint, verify responses |

### Phase 5: Data Migration (1 hour)

| # | Task | Details |
|---|---|---|
| 5.1 | Export D1 data | `wrangler d1 execute ... --json` |
| 5.2 | Transform to Turso SQL | Create `INSERT INTO` statements |
| 5.3 | Import to Turso | `turso db shell db-name < import.sql` |
| 5.4 | Verify data | `turso db shell db-name "SELECT COUNT(*) FROM subscribers"` |

### Phase 6: GitHub Actions Update (30 min)

| # | Task | Files | Details |
|---|---|---|---|
| 6.1 | Update `WORKER_SUBSCRIBERS_API` variable | GitHub repo settings → Variables | Update URL to Vercel endpoint |
| 6.2 | Verify daily workflow | `.github/workflows/daily.yml` | Run manual trigger, check subscriber fetch |

### Phase 7: Cleanup (30 min)

| # | Task | Details |
|---|---|---|
| 7.1 | Delete Cloudflare Worker | `wrangler delete social-hotspot-subscribe` |
| 7.2 | Delete Cloudflare D1 | `wrangler d1 delete social-hotspot-subscribe-db` |
| 7.3 | Remove `cloudflare-worker/` dir | `rm -rf cloudflare-worker/` |
| 7.4 | Remove wrangler dep from devDependencies | If listed |

---

## Appendix A: Key API Differences Reference

| Aspect | Cloudflare Worker | Vercel Serverless Function |
|---|---|---|
| Entry point | `export default { async fetch(request, env) {} }` | `export async function POST(request: Request) {}` |
| Environment vars | `env.RESEND_API_KEY` | `process.env.RESEND_API_KEY` |
| DB client | `env.DB.prepare(sql).bind(...)` | `db.execute({ sql, args: [...] })` |
| Response type | `new Response(...)` | `new Response(...)` (same!) |
| Redirect | `Response` with 302 + Location | Same — works identically |
| JSON response | `new Response(JSON.stringify(...))` | Same pattern |
| CORS OPTIONS | Handled in router | Must handle in each endpoint |
| Cold start | ~5ms (edge) | ~50-200ms (Vercel) |
| Timeout | 30s (free) | 10s (Hobby) — sufficient for all endpoints |
| Memory | 128MB | 1024MB (Hobby) |

## Appendix B: Vercel Hobby Plan Limits

| Limit | Value | Impact |
|---|---|---|
| Serverless Functions | 100 total | 7 endpoints — well within limit |
| Function invocations | 60/day (soft) | ~20-30/day expected (subscribe, verify, unsub requests) |
| Function duration | 10s max | All DB queries + Resend API calls < 5s |
| Bandwidth | 100GB | Trivial for API-only traffic |
| Edge Functions | N/A (not needed) | — |
| Concurrent builds | 1 | Fine for single-repo |

The only concern is the 60/day invocation limit. Current traffic is low (personal newsletter), so this is fine. If traffic grows, a Pro plan ($20/mo) removes the limit.

## Appendix C: Turnstile Free Tier Limits

| Limit | Value |
|---|---|
| Widget impressions | Unlimited |
| Siteverify API calls | Unlimited |
| Sites | Unlimited |
| Security | Cloudflare-managed ML bot detection |

Turnstile is fully free with no usage limits — ideal for this use case.
