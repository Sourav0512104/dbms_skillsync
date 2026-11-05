"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isRegister = mode === "register";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);

    const formData = new FormData(event.currentTarget);
    const payload = {
      ...(isRegister ? { full_name: formData.get("full_name") } : {}),
      email: formData.get("email"),
      password: formData.get("password"),
    };

    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        setError(typeof result.detail === "string" ? result.detail : "Please check your details and try again.");
        return;
      }
      router.replace("/dashboard");
      router.refresh();
    } catch {
      setError("We could not reach SkillSync. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <aside className="auth-aside">
        <Link className="wordmark" href="/">
          <span className="brand-mark">S</span>
          SkillSync
        </Link>
        <div className="auth-aside-copy">
          <span className="eyebrow">The work is better together</span>
          <h1>Find your people. Make it happen.</h1>
          <p>
            Build a profile that reflects how you work, find opportunities that
            fit, and meet collaborators who bring something new to the table.
          </p>
          <div className="auth-quote">
            “The best teams are not always the ones with the most in common.
            They are the ones who make each other better.”
          </div>
        </div>
        <div className="auth-footer">A more thoughtful way to build a team.</div>
      </aside>

      <section className="auth-panel">
        <form className="auth-form" onSubmit={submit}>
          <span className="eyebrow">{isRegister ? "Join the community" : "Welcome back"}</span>
          <h2>{isRegister ? "Create your account" : "Sign in to SkillSync"}</h2>
          <p>
            {isRegister
              ? "Start with a few details. You can build your profile next."
              : "Pick up where you left off and find your next opportunity."}
          </p>

          {isRegister && (
            <label className="field">
              Full name
              <input
                className="input"
                name="full_name"
                autoComplete="name"
                minLength={2}
                maxLength={120}
                placeholder="Your name"
                required
              />
            </label>
          )}

          <label className="field">
            Email address
            <input
              className="input"
              name="email"
              type="email"
              autoComplete="email"
              maxLength={254}
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="field">
            Password
            <input
              className="input"
              name="password"
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={isRegister ? 10 : 1}
              maxLength={128}
              placeholder={isRegister ? "At least 10 characters" : "Your password"}
              required
            />
          </label>

          {error && <div className="error-message" role="alert">{error}</div>}

          <button className="button" disabled={busy} type="submit">
            {busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
            {!busy && <span aria-hidden="true">→</span>}
          </button>

          <div className="auth-switch">
            {isRegister ? "Already have an account? " : "New to SkillSync? "}
            <Link href={isRegister ? "/login" : "/register"}>
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </div>
        </form>
      </section>
    </main>
  );
}
