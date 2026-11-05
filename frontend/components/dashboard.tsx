"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type User = {
  user_id: number;
  full_name: string;
  email: string;
  availability_hours: number;
  experience_years: number;
};

type Role = {
  role_id: number;
  title: string;
  role_type: string;
  slots_total: number;
  slots_filled: number;
  min_experience: number;
  project_id: number;
  project_name: string;
  project_type: string;
  skills: string[];
};

type Profile = {
  bio: string;
  resume_text: string;
  projects: string[];
  skills: string[];
  availability_hours: number;
  experience_years: number;
  profile_visible: boolean;
  user: User;
};

type Application = {
  application_id: number;
  status: string;
  applied_at: string;
  role_id: number;
  role_title: string;
  role_type: string;
  project_id: number;
  project_name: string;
};

type Candidate = {
  name: string;
  skills: string[];
  final_score: number;
  skill_overlap: number;
  experience_years: number;
  availability_hours: number;
};

type RoleDraft = {
  project_name: string;
  project_type: string;
  title: string;
  role_type: string;
  slots_total: number;
  min_experience: number;
  skills: string[];
};

type Analytics = {
  project_id: number;
  name: string;
  total_applications: number;
  accepted: number;
  pending: number;
  rejected: number;
};

type Section = "overview" | "discover" | "profile" | "applications" | "insights";
type ProfileDraft = Omit<Profile, "user"> & { full_name: string };

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent("skillsync:session-expired"));
    }
    throw new Error(typeof result.detail === "string" ? result.detail : "Something went wrong.");
  }
  return result as T;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? "")
    .join("")
    .toUpperCase();
}

function titleCase(value: string) {
  return value
    .split(/[_\s]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const navigation: { id: Section; label: string; symbol: string }[] = [
  { id: "overview", label: "Overview", symbol: "⌂" },
  { id: "discover", label: "Explore roles", symbol: "⌕" },
  { id: "profile", label: "My profile", symbol: "◉" },
  { id: "applications", label: "Applications", symbol: "▤" },
  { id: "insights", label: "Insights", symbol: "▥" },
];

const projectTypes = ["hackathon", "lab", "startup", "research", "competition"];
const roleTypes = [
  "frontend", "backend", "ml", "data", "devops", "design", "security", "research", "other",
];

export function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<ProfileDraft | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [roleCatalog, setRoleCatalog] = useState<Role[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [analytics, setAnalytics] = useState<Analytics[]>([]);
  const [section, setSection] = useState<Section>("overview");
  const [query, setQuery] = useState("");
  const [activeRole, setActiveRole] = useState<number | null>(null);
  const [matches, setMatches] = useState<Candidate[]>([]);
  const [busyRole, setBusyRole] = useState<number | null>(null);
  const [busyProfile, setBusyProfile] = useState(false);
  const [postingRole, setPostingRole] = useState(false);
  const [searchingRoles, setSearchingRoles] = useState(false);
  const [showRoleForm, setShowRoleForm] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    const [currentUser, currentProfile, currentRoles, currentApplications, currentAnalytics] =
      await Promise.all([
        api<User>("/api/auth/me"),
        api<Profile>("/api/profiles/me"),
        api<Role[]>("/api/roles"),
        api<Application[]>("/api/applications"),
        api<Analytics[]>("/api/analytics/project-summary"),
      ]);

    return {
      user: currentUser,
      profile: {
        full_name: currentProfile.user.full_name,
        bio: currentProfile.bio ?? "",
        resume_text: currentProfile.resume_text ?? "",
        projects: currentProfile.projects ?? [],
        skills: currentProfile.skills ?? [],
        availability_hours: currentProfile.user.availability_hours,
        experience_years: currentProfile.user.experience_years,
        profile_visible: currentProfile.profile_visible,
      },
      roles: currentRoles,
      applications: currentApplications,
      analytics: currentAnalytics,
    };
  }, []);

  const updateWorkspace = useCallback((data: Awaited<ReturnType<typeof loadData>>) => {
    setUser(data.user);
    setProfile(data.profile);
    setRoles(data.roles);
    setRoleCatalog(data.roles);
    setApplications(data.applications);
    setAnalytics(data.analytics);
  }, []);

  useEffect(() => {
    const expireSession = () => router.replace("/login");
    window.addEventListener("skillsync:session-expired", expireSession);
    return () => window.removeEventListener("skillsync:session-expired", expireSession);
  }, [router]);

  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        const data = await loadData();
        if (active) updateWorkspace(data);
      } catch (cause) {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to load your workspace.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, [loadData, updateWorkspace]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 3200);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const profileCompletion = useMemo(() => {
    if (!profile) return 0;
    const completed = [
      Boolean(profile.bio.trim()),
      Boolean(profile.resume_text.trim()),
      profile.skills.length > 0,
      profile.projects.length > 0,
      profile.experience_years > 0,
    ].filter(Boolean).length;
    return Math.round((completed / 5) * 100);
  }, [profile]);

  const filteredRoles = useMemo(() => {
    const searchTerm = query.trim().toLowerCase();
    if (!searchTerm) return roles;
    return roles.filter((role) =>
      `${role.title} ${role.project_name} ${role.role_type} ${role.project_type} ${role.skills.join(" ")}`
        .toLowerCase()
        .includes(searchTerm),
    );
  }, [query, roles]);

  const roleSuggestions = useMemo(
    () =>
      [...new Set(
        roleCatalog.flatMap((role) => [
          role.title,
          role.project_name,
          role.role_type,
          role.project_type,
          ...role.skills,
        ]),
      )].filter(Boolean),
    [roleCatalog],
  );

  async function searchRoles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSearchingRoles(true);
    try {
      const search = query.trim() ? `?search=${encodeURIComponent(query.trim())}` : "";
      setRoles(await api<Role[]>(`/api/roles${search}`));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Role search failed.");
    } finally {
      setSearchingRoles(false);
    }
  }

  async function postRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPostingRole(true);
    setError("");
    const formData = new FormData(event.currentTarget);
    const role: RoleDraft = {
      project_name: String(formData.get("project_name") ?? "").trim(),
      project_type: String(formData.get("project_type") ?? ""),
      title: String(formData.get("title") ?? "").trim(),
      role_type: String(formData.get("role_type") ?? ""),
      slots_total: Number(formData.get("slots_total")),
      min_experience: Number(formData.get("min_experience")),
      skills: String(formData.get("skills") ?? "")
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
    };

    try {
      await api("/api/roles", { method: "POST", body: JSON.stringify(role) });
      setQuery("");
      setShowRoleForm(false);
      setNotice("Your role is live. Teammates can now discover and apply.");
      updateWorkspace(await loadData());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Your role could not be published.");
    } finally {
      setPostingRole(false);
    }
  }

  async function applyToRole(role: Role) {
    setError("");
    try {
      await api("/api/applications", {
        method: "POST",
        body: JSON.stringify({ role_id: role.role_id }),
      });
      setNotice(`Your application for ${role.title} has been submitted.`);
      updateWorkspace(await loadData());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Your application could not be submitted.");
    }
  }

  async function findMatches(role: Role) {
    setActiveRole(role.role_id);
    setBusyRole(role.role_id);
    setError("");
    try {
      const result = await api<{ matches: Candidate[] }>("/api/match", {
        method: "POST",
        body: JSON.stringify({ role_id: role.role_id, top_k: 5, candidate_pool: 50, rerank: true }),
      });
      setMatches(result.matches);
      setSection("discover");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We could not find matches for this role.");
    } finally {
      setBusyRole(null);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setBusyProfile(true);
    setError("");
    const formData = new FormData(event.currentTarget);
    const update: ProfileDraft = {
      full_name: String(formData.get("full_name") ?? "").trim(),
      bio: String(formData.get("bio") ?? "").trim(),
      resume_text: String(formData.get("resume_text") ?? "").trim(),
      projects: String(formData.get("projects") ?? "")
        .split("\n")
        .map((project) => project.trim())
        .filter(Boolean),
      skills: String(formData.get("skills") ?? "")
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
      availability_hours: Number(formData.get("availability_hours")),
      experience_years: Number(formData.get("experience_years")),
      profile_visible: formData.get("profile_visible") === "on",
    };

    try {
      await api("/api/profiles/me", { method: "PUT", body: JSON.stringify(update) });
      setNotice("Your profile has been updated.");
      updateWorkspace(await loadData());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Your profile could not be saved.");
    } finally {
      setBusyProfile(false);
    }
  }

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/");
    router.refresh();
  }

  if (loading) {
    return <main className="loading-page">Preparing your SkillSync workspace…</main>;
  }

  if (!user || !profile) {
    return (
      <main className="loading-page">
        <div>
          <div className="error-message">{error || "Your workspace could not be loaded."}</div>
          <p><Link href="/login">Return to sign in</Link></p>
        </div>
      </main>
    );
  }

  const pageTitles: Record<Section, string> = {
    overview: "Your workspace",
    discover: "Explore opportunities",
    profile: "Your profile",
    applications: "Your applications",
    insights: "Project insights",
  };
  const appliedRoleIds = new Set(applications.map((application) => application.role_id));
  const displayedRoles = section === "overview" ? filteredRoles.slice(0, 4) : filteredRoles;

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <Link className="wordmark" href="/">
          <span className="brand-mark">S</span>
          SkillSync
        </Link>
        <nav className="sidebar-nav" aria-label="Main navigation">
          <div className="side-label">Workspace</div>
          {navigation.map((item) => (
            <button
              aria-current={section === item.id ? "page" : undefined}
              aria-label={item.label}
              className={`side-link ${section === item.id ? "active" : ""}`}
              key={item.id}
              onClick={() => {
                setSection(item.id);
                setError("");
              }}
              type="button"
            >
              <span className="side-symbol" aria-hidden="true">{item.symbol}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button
          aria-label="Sign out"
          className="mobile-signout side-link"
          onClick={signOut}
          type="button"
        >
          <span className="side-symbol" aria-hidden="true">↪</span>
          <span>Sign out</span>
        </button>
        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <span className="avatar">{initials(user.full_name)}</span>
            <div>
              <strong>{user.full_name}</strong>
              <span>Member account</span>
            </div>
          </div>
          <button className="side-link" onClick={signOut} type="button">
            <span className="side-symbol" aria-hidden="true">↪</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <section className="dashboard-main">
        <header className="dashboard-header">
          <div>
            <h1>{pageTitles[section]}</h1>
            <p>A considered space to find your next great collaboration.</p>
          </div>
          <div className="header-user">
            <span className="avatar">{initials(user.full_name)}</span>
            <div className="user-meta">
              <strong>{user.full_name}</strong>
              <span>{user.email}</span>
            </div>
          </div>
        </header>

        {error && <div className="error-message" role="alert">{error}</div>}

        {section === "overview" && (
          <>
            <section className="welcome-banner">
              <div className="welcome-copy">
                <span className="eyebrow">Good to have you here</span>
                <h2>Make your next idea a team effort, {user.full_name.split(" ")[0]}.</h2>
                <p>
                  A thoughtful profile helps people see what you bring. Explore
                  open roles and find collaborators whose skills complement yours.
                </p>
              </div>
              <button className="button" onClick={() => setSection("discover")} type="button">
                Explore roles <span aria-hidden="true">→</span>
              </button>
            </section>

            <div className="metric-grid">
              <div className="metric-card">
                <span className="metric-label">Open opportunities</span>
                <strong className="metric-value">{roles.length}</strong>
                <span className="metric-note">Across projects looking for people</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Applications</span>
                <strong className="metric-value">{applications.length}</strong>
                <span className="metric-note">Your current project conversations</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Profile strength</span>
                <strong className="metric-value">{profileCompletion}%</strong>
                <span className="metric-note">Add detail to make a better first impression</span>
              </div>
            </div>

            <div className="section-heading">
              <div>
                <h2>Opportunities worth a look</h2>
                <p>Open roles across projects and research teams.</p>
              </div>
              <button className="button secondary small" onClick={() => setSection("discover")} type="button">
                Browse all
              </button>
            </div>
            <RoleGrid
              appliedRoleIds={appliedRoleIds}
              busyRole={busyRole}
              emptyMessage={
                roleCatalog.length
                  ? "No open roles are available right now."
                  : "No roles are available yet. Post one from Explore roles or initialize the demo dataset with: docker compose exec api python -m app.bootstrap"
              }
              onApply={applyToRole}
              onMatch={findMatches}
              roles={displayedRoles}
            />
          </>
        )}

        {section === "discover" && (
          <>
            <section className="content-card">
              <div className="section-heading discover-heading" style={{ marginTop: 0 }}>
                <div>
                  <h2>Find a project that fits</h2>
                  <p>Search by role, skill, project name, or area of work.</p>
                </div>
                <button
                  className="button"
                  onClick={() => setShowRoleForm((visible) => !visible)}
                  type="button"
                >
                  {showRoleForm ? "Cancel" : "Post a role"}
                </button>
              </div>
              <form className="search-row" onSubmit={searchRoles}>
                <input
                  aria-label="Search projects and roles"
                  className="input"
                  list="role-search-suggestions"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Try “frontend”, “research”, or “healthcare”"
                  value={query}
                />
                <datalist id="role-search-suggestions">
                  {roleSuggestions.map((suggestion) => (
                    <option key={suggestion} value={suggestion} />
                  ))}
                </datalist>
                <button className="button" disabled={searchingRoles} type="submit">
                  {searchingRoles ? "Searching…" : "Search roles"}
                </button>
              </form>
              {showRoleForm && (
                <form className="role-post-form" onSubmit={postRole}>
                  <div className="form-two">
                    <label className="field">
                      Project name
                      <input className="input" maxLength={160} minLength={2} name="project_name" required />
                    </label>
                    <label className="field">
                      Project type
                      <select className="input" name="project_type">
                        {projectTypes.map((type) => (
                          <option key={type} value={type}>{titleCase(type)}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="form-two">
                    <label className="field">
                      Role title
                      <input className="input" maxLength={160} minLength={2} name="title" required />
                    </label>
                    <label className="field">
                      Role area
                      <select className="input" name="role_type">
                        {roleTypes.map((type) => (
                          <option key={type} value={type}>
                            {type === "ml" ? "Machine learning" : titleCase(type)}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="form-two">
                    <label className="field">
                      Open spots
                      <input className="input" defaultValue={2} max={20} min={1} name="slots_total" type="number" />
                    </label>
                    <label className="field">
                      Minimum experience (years)
                      <input className="input" defaultValue={0} max={70} min={0} name="min_experience" step="0.5" type="number" />
                    </label>
                  </div>
                  <label className="field">
                    Required skills
                    <input
                      className="input"
                      maxLength={2000}
                      name="skills"
                      placeholder="Python, FastAPI, PostgreSQL"
                      required
                    />
                    <span className="muted">Separate skills with commas. Your role will be visible to everyone.</span>
                  </label>
                  <button className="button" disabled={postingRole} type="submit">
                    {postingRole ? "Publishing role…" : "Publish role"}
                  </button>
                </form>
              )}
            </section>
            <div className="section-heading">
              <div>
                <h2>{filteredRoles.length} open {filteredRoles.length === 1 ? "role" : "roles"}</h2>
                <p>Each role is a chance to bring your skills to a real project.</p>
              </div>
            </div>
            <RoleGrid
              appliedRoleIds={appliedRoleIds}
              busyRole={busyRole}
              emptyMessage={
                roleCatalog.length
                  ? `No open roles match "${query.trim()}". Try another role, skill, or project name.`
                  : "There are no roles to search yet. Post a role, or initialize the demo dataset with: docker compose exec api python -m app.bootstrap"
              }
              onApply={applyToRole}
              onMatch={findMatches}
              roles={displayedRoles}
            />
            {activeRole !== null && (
              <section className="match-panel">
                <h3>People whose experience complements this role</h3>
                {matches.length === 0 ? (
                  <div className="empty-state">No profile-visible matches were found for this role yet.</div>
                ) : matches.map((candidate, index) => (
                  <div className="match-row" key={`${candidate.name}-${index}`}>
                    <span className={`avatar ${index % 2 ? "warm" : ""}`}>{initials(candidate.name)}</span>
                    <div>
                      <strong>{candidate.name}</strong>
                      <span>
                        {candidate.experience_years} yrs experience · {candidate.availability_hours} hrs/week
                      </span>
                      <span>{candidate.skills.slice(0, 4).join(" · ") || "Skills not listed"}</span>
                    </div>
                    <span className="match-score">{Math.round(candidate.final_score * 100)}% match</span>
                  </div>
                ))}
              </section>
            )}
          </>
        )}

        {section === "profile" && (
          <section className="content-card">
            <div className="profile-heading">
              <div>
                <h2>Tell people how you like to work</h2>
                <p>Your profile helps teams understand your experience and interests.</p>
              </div>
              <span className="score-badge">{profileCompletion}% complete</span>
            </div>
            <form className="profile-form" onSubmit={saveProfile}>
              <label className="field">
                Full name
                <input
                  className="input"
                  defaultValue={profile.full_name}
                  maxLength={120}
                  minLength={2}
                  name="full_name"
                  required
                />
              </label>
              <div className="form-two">
                <label className="field">
                  Experience (years)
                  <input
                    className="input"
                    defaultValue={profile.experience_years}
                    max={70}
                    min={0}
                    name="experience_years"
                    step="0.5"
                    type="number"
                  />
                </label>
                <label className="field">
                  Weekly availability (hours)
                  <input
                    className="input"
                    defaultValue={profile.availability_hours}
                    max={80}
                    min={0}
                    name="availability_hours"
                    type="number"
                  />
                </label>
              </div>
              <label className="field">
                About you
                <textarea
                  className="textarea"
                  defaultValue={profile.bio}
                  maxLength={5000}
                  name="bio"
                  placeholder="A short introduction: what you do, what interests you, and how you work best."
                />
              </label>
              <label className="field">
                Skills
                <input
                  className="input"
                  defaultValue={profile.skills.join(", ")}
                  name="skills"
                  placeholder="Python, product design, data analysis"
                />
                <span className="muted">Separate skills with commas.</span>
              </label>
              <label className="field">
                Selected projects
                <textarea
                  className="textarea"
                  defaultValue={profile.projects.join("\n")}
                  name="projects"
                  placeholder="One project per line"
                />
              </label>
              <label className="field">
                Experience and interests
                <textarea
                  className="textarea"
                  defaultValue={profile.resume_text}
                  maxLength={20000}
                  name="resume_text"
                  placeholder="Add relevant experience, tools you know, or the kinds of problems you enjoy solving."
                />
              </label>
              <label className="visibility-row">
                <input defaultChecked={profile.profile_visible} name="profile_visible" type="checkbox" />
                Make my profile available for teammate matching
              </label>
              <div>
                <button className="button" disabled={busyProfile} type="submit">
                  {busyProfile ? "Saving profile…" : "Save profile"}
                </button>
              </div>
            </form>
          </section>
        )}

        {section === "applications" && (
          <section className="content-card">
            <div className="profile-heading">
              <div>
                <h2>Applications and project conversations</h2>
                <p>Keep track of the roles you have applied to.</p>
              </div>
              <span className="score-badge">{applications.length} total</span>
            </div>
            {applications.length === 0 ? (
              <div className="empty-state">
                <strong>Your next project could start here.</strong>
                Explore opportunities and apply to a role that feels like a good fit.
                <p><button className="button small" onClick={() => setSection("discover")} type="button">Explore roles</button></p>
              </div>
            ) : (
              <div className="application-list">
                {applications.map((application) => (
                  <div className="application-row" key={application.application_id}>
                    <div>
                      <h3>{application.role_title}</h3>
                      <p>{application.project_name} · Applied {new Date(application.applied_at).toLocaleDateString()}</p>
                    </div>
                    <span className={`status-pill ${application.status}`}>{titleCase(application.status)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {section === "insights" && (
          <section className="content-card">
            <div className="profile-heading">
              <div>
                <h2>Project activity</h2>
                <p>A snapshot of applications across the SkillSync community.</p>
              </div>
            </div>
            {analytics.length === 0 ? (
              <div className="empty-state">Project insights will appear as teams receive applications.</div>
            ) : (
              <div className="application-list">
                {analytics.map((project) => (
                  <div className="application-row" key={project.project_id}>
                    <div>
                      <h3>{project.name}</h3>
                      <p>{project.total_applications} applications · {project.pending} awaiting a response</p>
                    </div>
                    <span className="status-pill accepted">{project.accepted} accepted</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </section>

      {notice && <div className="toast" role="status">{notice}</div>}
    </main>
  );
}

function RoleGrid({
  roles,
  appliedRoleIds,
  busyRole,
  emptyMessage,
  onApply,
  onMatch,
}: {
  roles: Role[];
  appliedRoleIds: Set<number>;
  busyRole: number | null;
  emptyMessage: string;
  onApply: (role: Role) => void;
  onMatch: (role: Role) => void;
}) {
  if (!roles.length) {
    return (
      <section className="content-card empty-state">
        <strong>{emptyMessage}</strong>
      </section>
    );
  }

  return (
    <div className="role-grid">
      {roles.map((role) => {
        const remaining = Math.max(0, role.slots_total - role.slots_filled);
        const alreadyApplied = appliedRoleIds.has(role.role_id);
        return (
          <article className="role-card" key={role.role_id}>
            <div className="role-card-top">
              <div>
                <h3>{role.title}</h3>
                <p>{role.project_name}</p>
              </div>
              <span className="role-availability">{remaining} {remaining === 1 ? "spot" : "spots"}</span>
            </div>
            <div className="skill-list">
              {role.skills.slice(0, 3).map((skill) => (
                <span className="skill-chip" key={skill}>{skill}</span>
              ))}
              <span className="skill-chip">{titleCase(role.project_type)}</span>
            </div>
            <div className="role-card-footer">
              <button
                className="button secondary small"
                disabled={busyRole === role.role_id}
                onClick={() => onMatch(role)}
                type="button"
              >
                {busyRole === role.role_id ? "Finding people…" : "Find teammates"}
              </button>
              <button
                className={`button small ${alreadyApplied ? "quiet" : ""}`}
                disabled={alreadyApplied || remaining === 0}
                onClick={() => onApply(role)}
                type="button"
              >
                {alreadyApplied ? "Applied" : remaining === 0 ? "Full" : "Apply"}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
