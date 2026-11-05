import Link from "next/link";

const previewPeople = [
  { initials: "AK", name: "Aarav Kumar", focus: "Product design · 4 yrs", score: "94%", tone: "" },
  { initials: "MS", name: "Maya Singh", focus: "Frontend · 3 yrs", score: "89%", tone: "warm" },
  { initials: "JR", name: "Jordan Reyes", focus: "Machine learning · 5 yrs", score: "86%", tone: "lilac" },
];

const features = [
  {
    icon: "↗",
    title: "Meet your next collaborator",
    description: "Find people with complementary skills, relevant experience, and time for your project.",
  },
  {
    icon: "◎",
    title: "Make the fit easy to see",
    description: "Clear match explanations help you understand how skills and project needs line up.",
  },
  {
    icon: "⌂",
    title: "Keep your work in one place",
    description: "Showcase your profile, track applications, and discover open roles from one workspace.",
  },
];

export default function HomePage() {
  return (
    <main className="landing">
      <nav className="landing-nav">
        <Link className="wordmark" href="/" aria-label="SkillSync home">
          <span className="brand-mark">S</span>
          SkillSync
        </Link>
        <div className="nav-links">
          <a href="#how-it-works">How it works</a>
          <Link href="/login">Sign in</Link>
          <Link className="button small" href="/register">Get started <span aria-hidden="true">→</span></Link>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="hero-copy">
          <span className="eyebrow">Good work starts with good people</span>
          <h1>Find the right people to <span>build what matters.</span></h1>
          <p>
            SkillSync brings project opportunities and complementary talent
            together, so your next great idea does not have to stay an idea.
          </p>
          <div className="hero-actions">
            <Link className="button" href="/register">Create your free profile <span aria-hidden="true">→</span></Link>
            <Link className="button secondary" href="/login">Explore your workspace</Link>
          </div>
          <div className="hero-note">Thoughtful matches. Clear expectations. Better teams.</div>
        </div>

        <div className="preview-wrap" aria-label="Preview of recommended collaborators">
          <div className="hero-orbit" />
          <div className="preview-card">
            <div className="preview-top">
              <strong>People who fit your next project</strong>
              <span className="preview-count">Top matches</span>
            </div>
            <div className="preview-role">For · Sustainable city guide</div>
            {previewPeople.map((person) => (
              <div className="preview-person" key={person.name}>
                <span className={`avatar ${person.tone}`}>{person.initials}</span>
                <span className="person-detail">
                  <strong>{person.name}</strong>
                  <span>{person.focus}</span>
                </span>
                <span className="score-badge">{person.score}</span>
              </div>
            ))}
            <div className="preview-score">
              <span>Skills, experience and availability considered</span>
              <strong>See why people match</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-proof" aria-label="Platform benefits">
        <div className="proof-item">
          <strong>Skills-first discovery</strong>
          <span>Find collaborators beyond job titles</span>
        </div>
        <div className="proof-item">
          <strong>Built for real projects</strong>
          <span>Explore research, startups and more</span>
        </div>
        <div className="proof-item">
          <strong>Your profile, your choice</strong>
          <span>Control what is visible to others</span>
        </div>
      </section>

      <section className="landing-features" id="how-it-works">
        <span className="eyebrow">A better way to team up</span>
        <h2>Make room for good ideas and the people behind them.</h2>
        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <span className="feature-icon" aria-hidden="true">{feature.icon}</span>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
