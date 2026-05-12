"use client";

import { useState } from "react";
import Script from "next/script";

export default function SubscribePage() {
  const [email, setEmail] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!turnstileToken) {
      setMessage({ type: "error", text: "Please complete the bot verification." });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const resp = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, turnstile_token: turnstileToken }),
      });
      const data = await resp.json();

      if (resp.ok) {
        setMessage({ type: "success", text: data.message });
      } else {
        setMessage({ type: "error", text: data.error || "Something went wrong." });
        // Reset Turnstile
        if (typeof window !== "undefined" && (window as any).turnstile) {
          (window as any).turnstile.reset();
        }
        setTurnstileToken("");
      }
    } catch {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js"
        async
        defer
      />

      <div
        style={{
          maxWidth: "480px",
          width: "100%",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "16px",
          padding: "40px 32px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>📧</div>
        <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}>
          Tech Hotspot Daily
        </h1>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "15px",
            marginBottom: "32px",
          }}
        >
          Get curated tech & AI news delivered to your inbox every morning.
        </p>

        <div
          style={{
            textAlign: "left",
            background: "var(--surface-2)",
            borderRadius: "12px",
            padding: "20px",
            marginBottom: "24px",
          }}
        >
          <h3
            style={{
              fontSize: "13px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              color: "var(--text-secondary)",
              marginBottom: "12px",
            }}
          >
            What you&apos;ll get
          </h3>
          <ul style={{ listStyle: "none", fontSize: "14px" }}>
            {[
              "AI-generated summaries of top stories",
              "Sources from HN, Reddit, Twitter, 知乎, 微博",
              '"Why it matters" insights for IT professionals',
              "Beautiful dark-mode email, mobile-friendly",
              "Unsubscribe anytime, no spam ever",
            ].map((item) => (
              <li
                key={item}
                style={{ padding: "6px 0", color: "var(--text)" }}
              >
                ✓ {item}
              </li>
            ))}
          </ul>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              style={{
                width: "100%",
                padding: "14px 16px",
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                color: "var(--text)",
                fontSize: "15px",
                fontFamily: "inherit",
                outline: "none",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
            />
          </div>

          <div
            className="cf-turnstile"
            data-sitekey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "0x4AAAAAADNpNH0Lt6fj8DKd"}
            data-theme="dark"
            data-callback={(token: string) => setTurnstileToken(token)}
            style={{
              marginBottom: "16px",
              display: "flex",
              justifyContent: "center",
            }}
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "14px",
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: "10px",
              fontSize: "15px",
              fontWeight: 600,
              fontFamily: "inherit",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Processing..." : "Subscribe"}
          </button>
        </form>

        {message && (
          <div
            style={{
              marginTop: "16px",
              padding: "12px",
              borderRadius: "8px",
              fontSize: "14px",
              background:
                message.type === "success"
                  ? "rgba(16, 185, 129, 0.1)"
                  : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${
                message.type === "success" ? "var(--success)" : "var(--error)"
              }`,
              color:
                message.type === "success" ? "var(--success)" : "var(--error)",
            }}
          >
            {message.text}
          </div>
        )}

        <p
          style={{
            marginTop: "20px",
            fontSize: "12px",
            color: "var(--text-secondary)",
          }}
        >
          🔒 We respect your privacy. No spam, no sharing, unsubscribe anytime.
        </p>
        <a
          href="/"
          style={{
            display: "inline-block",
            marginTop: "24px",
            color: "var(--text-secondary)",
            textDecoration: "none",
            fontSize: "14px",
          }}
        >
          ← Back to Daily Report
        </a>
      </div>
    </div>
  );
}
