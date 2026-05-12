"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function UnsubscribeContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");

  const config: Record<string, { icon: string; title: string; message: string }> = {
    success: {
      icon: "👋",
      title: "Unsubscribed",
      message:
        'You have been successfully unsubscribed. If you change your mind, you can always subscribe again.',
    },
    invalid: {
      icon: "❌",
      title: "Invalid Email",
      message: "The email address provided is not valid.",
    },
    notfound: {
      icon: "🔍",
      title: "Email Not Found",
      message: "This email was not found in our subscriber list.",
    },
    error: {
      icon: "⚠️",
      title: "Something Went Wrong",
      message: "An error occurred. Please try again.",
    },
  };

  const result = config[status || ""] || {
    icon: "👋",
    title: "Unsubscribed",
    message:
      'You have been successfully unsubscribed. If you change your mind, you can always subscribe again.',
  };

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

export default function UnsubscribePage() {
  return (
    <Suspense
      fallback={
        <div className="loading">
          <div className="spinner"></div>
        </div>
      }
    >
      <UnsubscribeContent />
    </Suspense>
  );
}
