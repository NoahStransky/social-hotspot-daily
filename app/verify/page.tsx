"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function VerifyContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");

  const config: Record<string, { icon: string; title: string; message: string }> = {
    success: {
      icon: "✅",
      title: "Subscription Verified!",
      message:
        "Thank you! You will now receive daily tech news in your inbox. Your first email is coming tomorrow morning.",
    },
    already: {
      icon: "👍",
      title: "Already Verified",
      message: "This email was already verified. You're all set!",
    },
    invalid: {
      icon: "❌",
      title: "Invalid Link",
      message:
        "This verification link is invalid or has expired. Please try subscribing again.",
    },
    error: {
      icon: "⚠️",
      title: "Something Went Wrong",
      message: "An error occurred. Please try again.",
    },
  };

  const result = config[status || ""] || config.invalid;

  return (
    <div className="container" style={{ textAlign: "center", paddingTop: "80px" }}>
      <div style={{ fontSize: "48px", marginBottom: "16px" }}>{result.icon}</div>
      <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "12px" }}>
        {result.title}
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "15px", lineHeight: 1.6 }}>
        {result.message}
      </p>
      <a
        href="/"
        style={{
          display: "inline-block",
          marginTop: "24px",
          color: "var(--accent)",
          fontSize: "14px",
        }}
      >
        ← Back to Daily Report
      </a>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="loading">
          <div className="spinner"></div>
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
