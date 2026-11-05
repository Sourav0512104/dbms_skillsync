import argparse
import random

from faker import Faker

from .db import pg_conn, profiles
from .semantic import embed

fake = Faker()
Faker.seed(42)
random.seed(42)

SKILLS = [
    ("Python", "backend"),
    ("Java", "backend"),
    ("C++", "backend"),
    ("FastAPI", "backend"),
    ("Django", "backend"),
    ("Node.js", "backend"),
    ("React", "frontend"),
    ("Next.js", "frontend"),
    ("Vue", "frontend"),
    ("TypeScript", "frontend"),
    ("JavaScript", "frontend"),
    ("HTML/CSS", "frontend"),
    ("Figma", "design"),
    ("UI/UX", "design"),
    ("PostgreSQL", "data"),
    ("MongoDB", "data"),
    ("Redis", "backend"),
    ("SQL", "data"),
    ("Pandas", "data"),
    ("PyTorch", "ml"),
    ("TensorFlow", "ml"),
    ("Scikit-learn", "ml"),
    ("NLP", "ml"),
    ("Computer Vision", "ml"),
    ("Docker", "devops"),
    ("Kubernetes", "devops"),
    ("AWS", "devops"),
    ("Cybersecurity", "security"),
    ("Research", "research"),
    ("Statistics", "research"),
]

TECHNOLOGY_DESCRIPTIONS = {
    name: f"{name} software development technology and project experience"
    for name, _ in SKILLS
}

DEMO_PERSONAS = [
    {
        "name": "Avery Chen",
        "skills": ["React", "Next.js", "TypeScript", "Figma", "UI/UX"],
        "bio": "Frontend developer who cares about accessible, polished interfaces and clear design systems.",
        "resume": "Built responsive Next.js products with React and TypeScript; partnered with designers in Figma.",
        "projects": ["Designed a campus event discovery app"],
    },
    {
        "name": "Jordan Okafor",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
        "bio": "Backend engineer interested in dependable APIs, thoughtful data models, and developer tooling.",
        "resume": "Created FastAPI services with PostgreSQL persistence, Redis caching, and Docker-based delivery.",
        "projects": ["Built an API for a student services platform"],
    },
    {
        "name": "Anupam",
        "skills": ["Python", "PyTorch", "NLP", "Research", "Statistics"],
        "bio": "Machine learning researcher exploring language technology for practical, human-centered products.",
        "resume": "Evaluated NLP models in PyTorch and documented experiments with reproducible statistical analysis.",
        "projects": ["Prototyped a clinical note summarizer"],
    },
    {
        "name": "Mateo Silva",
        "skills": ["Python", "PostgreSQL", "Pandas", "SQL", "Statistics"],
        "bio": "Data analyst who turns messy operational data into useful, well-explained decisions.",
        "resume": "Built repeatable SQL and Pandas pipelines and presented statistical findings to project teams.",
        "projects": ["Analyzed bus reliability and commuter patterns"],
    },
    {
        "name": "Priya Nair",
        "skills": ["Figma", "UI/UX", "React", "TypeScript", "HTML/CSS"],
        "bio": "Product designer comfortable moving from user research and wireframes to frontend prototypes.",
        "resume": "Ran usability sessions, created Figma design systems, and implemented React interface prototypes.",
        "projects": ["Designed an inclusive peer-learning experience"],
    },
    {
        "name": "Noah Williams",
        "skills": ["Docker", "Kubernetes", "AWS", "Python", "Redis"],
        "bio": "DevOps contributor focused on practical cloud deployments, observability, and smooth team handoffs.",
        "resume": "Containerized Python services and practiced deployment workflows with AWS and Kubernetes.",
        "projects": ["Automated deployment for a research dashboard"],
    },
    {
        "name": "Imani Brooks",
        "skills": ["Cybersecurity", "Python", "Docker", "AWS", "Research"],
        "bio": "Security-minded developer interested in threat modeling, safer defaults, and privacy-aware products.",
        "resume": "Reviewed application security, automated small checks in Python, and wrote actionable research notes.",
        "projects": ["Created a secure file-sharing prototype"],
    },
    {
        "name": "Elena Petrova",
        "skills": ["Research", "Statistics", "Python", "Scikit-learn", "Pandas"],
        "bio": "Research analyst who enjoys careful evaluation, reproducible notebooks, and communicating uncertainty.",
        "resume": "Applied statistical methods and Scikit-learn baselines to small research datasets in Python.",
        "projects": ["Studied factors affecting student wellbeing"],
    },
    {
        "name": "Ravi Patel",
        "skills": ["Computer Vision", "PyTorch", "Python", "TensorFlow", "Research"],
        "bio": "Computer vision enthusiast interested in responsible image analysis and real-world evaluation.",
        "resume": "Trained and compared PyTorch and TensorFlow vision models with clear evaluation reports.",
        "projects": ["Explored flood impact mapping from satellite images"],
    },
    {
        "name": "Maya Thompson",
        "skills": ["Node.js", "React", "JavaScript", "MongoDB", "SQL"],
        "bio": "Full-stack builder who likes shipping useful web tools and collaborating across product disciplines.",
        "resume": "Developed JavaScript applications with React, Node.js, MongoDB, and relational databases.",
        "projects": ["Built a shared equipment booking tool"],
    },
    {
        "name": "Luca Moretti",
        "skills": ["Figma", "UI/UX", "HTML/CSS", "Vue", "JavaScript"],
        "bio": "Interaction designer and prototyper who makes complex workflows feel approachable.",
        "resume": "Mapped user journeys, tested prototypes, and built Vue and HTML/CSS interaction demos.",
        "projects": ["Redesigned a community resource finder"],
    },
    {
        "name": "Zoe Kim",
        "skills": ["Vue", "JavaScript", "HTML/CSS", "Node.js", "MongoDB"],
        "bio": "Web developer who enjoys collaborative product work, clean UI, and learning new frameworks.",
        "resume": "Built Vue interfaces and Node.js features for student-focused web projects.",
        "projects": ["Created a collaborative study planner"],
    },
]


def main(reset: bool = False, if_missing: bool = False) -> None:
    if if_missing and not reset:
        with pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        (
                            SELECT count(*)
                            FROM users
                            WHERE email LIKE 'demo%@skillsync.local'
                               OR email LIKE 'user%@skillsync.local'
                        ) AS seeded_users,
                        (
                            SELECT count(DISTINCT p.project_id)
                            FROM projects p
                            JOIN users u ON u.user_id = p.owner_id
                            WHERE u.email = 'demo1@skillsync.local'
                        ) AS seeded_projects,
                        (
                            SELECT count(*)
                            FROM project_roles r
                            JOIN projects p ON p.project_id = r.project_id
                            JOIN users u ON u.user_id = p.owner_id
                            WHERE u.email = 'demo1@skillsync.local'
                        ) AS seeded_roles
                    """
                )
                seeded = cur.fetchone()
        if (
            seeded["seeded_users"] >= 250
            and seeded["seeded_projects"] >= 5
            and seeded["seeded_roles"] >= 20
            and profiles.count_documents({"user_id": {"$exists": True}}) >= 250
        ):
            print("Demo dataset already initialized; skipping seed.")
            return

    with pg_conn() as conn:
        with conn.cursor() as cur:
            if reset:
                cur.execute(
                    """
                    TRUNCATE applications, role_skills, project_roles, milestones,
                             projects, user_skills, skills, users
                    RESTART IDENTITY CASCADE
                    """
                )
            cur.executemany(
                """
                INSERT INTO skills (canonical_name, category, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (canonical_name) DO NOTHING
                """,
                [
                    (name, category, TECHNOLOGY_DESCRIPTIONS[name])
                    for name, category in SKILLS
                ],
            )

            member_profiles = [
                {
                    **persona,
                    "email": f"demo{index}@skillsync.local",
                    "availability_hours": random.randint(8, 24),
                    "experience_years": round(random.uniform(0.5, 6), 1),
                }
                for index, persona in enumerate(DEMO_PERSONAS, start=1)
            ]
            while len(member_profiles) < 250:
                member_profiles.append(
                    {
                        "name": fake.name(),
                        "email": f"user{len(member_profiles) + 1}@skillsync.local",
                        "availability_hours": random.randint(5, 30),
                        "experience_years": round(random.random() * 6, 1),
                        "skills": [],
                        "bio": "",
                        "resume": "",
                        "projects": [],
                    }
                )
            user_ids = []
            for member in member_profiles:
                cur.execute(
                    """
                    INSERT INTO users (
                        full_name, email, availability_hours,
                        experience_years, profile_visible
                    )
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (email) DO UPDATE SET profile_visible = TRUE
                    RETURNING user_id
                    """,
                    (
                        member["name"],
                        member["email"],
                        member["availability_hours"],
                        member["experience_years"],
                    ),
                )
                user_ids.append(cur.fetchone()["user_id"])

            skill_ids = {
                row["canonical_name"]: row["skill_id"]
                for row in cur.execute(
                    "SELECT skill_id, canonical_name FROM skills"
                ).fetchall()
            }
            user_skills = []
            documents = []

            for user_id, member in zip(user_ids, member_profiles):
                skill_names = member["skills"] or [
                    name for name, _ in random.sample(SKILLS, random.randint(3, 7))
                ]
                user_skills.extend(
                    (
                        user_id,
                        skill_ids[name],
                        random.randint(2, 5),
                        round(random.random() * 4, 1),
                    )
                    for name in skill_names
                )

                bio = member["bio"] or (
                    f"Student developer interested in {', '.join(skill_names[:3])}. "
                    + " ".join(TECHNOLOGY_DESCRIPTIONS[name] for name in skill_names)
                )
                resume = member["resume"] or (
                    f"Experience with {', '.join(skill_names)}. "
                    "Built academic and hackathon projects involving "
                    + " ".join(TECHNOLOGY_DESCRIPTIONS[name] for name in skill_names)
                )
                second_skill = skill_names[1] if len(skill_names) > 1 else skill_names[0]
                documents.append(
                    {
                        "user_id": user_id,
                        "bio": bio,
                        "resume_text": resume,
                        "projects": member["projects"] or [
                            f"Project using {skill_names[0]} and {second_skill}"
                        ],
                        "skills_text": skill_names,
                    }
                )

            cur.executemany(
                """
                INSERT INTO user_skills (user_id, skill_id, proficiency, years_used)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, skill_id) DO UPDATE
                SET proficiency = EXCLUDED.proficiency,
                    years_used = EXCLUDED.years_used
                """,
                user_skills,
            )
        conn.commit()

    profile_texts = [
        " ".join(
            [
                document["bio"],
                document["resume_text"],
                " ".join(document["projects"]),
                " ".join(document["skills_text"]),
            ]
        )
        for document in documents
    ]
    embeddings = embed(profile_texts).tolist()
    if reset:
        profiles.delete_many({})
    for document, vector in zip(documents, embeddings):
        profiles.update_one(
            {"user_id": document["user_id"]},
            {"$set": {**document, "embedding": vector}},
            upsert=True,
        )

    with pg_conn() as conn:
        with conn.cursor() as cur:
            skill_ids = {
                row["canonical_name"]: row["skill_id"]
                for row in cur.execute(
                    "SELECT skill_id, canonical_name FROM skills"
                ).fetchall()
            }
            demo_projects = [
                (
                    "AI-powered healthcare assistant",
                    "hackathon",
                    [
                        ("Frontend Engineer", "frontend", ["React", "Next.js", "TypeScript"]),
                        ("ML Engineer", "ml", ["Python", "PyTorch", "NLP"]),
                        ("Product Designer", "design", ["Figma", "UI/UX", "React"]),
                        ("Backend Engineer", "backend", ["Python", "FastAPI", "PostgreSQL"]),
                    ],
                ),
                (
                    "Urban mobility analytics",
                    "research",
                    [
                        ("Data Engineer", "data", ["Python", "PostgreSQL", "Pandas"]),
                        ("Research Analyst", "research", ["Research", "Statistics", "Scikit-learn"]),
                        ("Dashboard Developer", "frontend", ["Vue", "JavaScript", "HTML/CSS"]),
                        ("Platform Engineer", "devops", ["Docker", "AWS", "Kubernetes"]),
                    ],
                ),
                (
                    "Campus collaboration platform",
                    "lab",
                    [
                        ("Full-stack Developer", "backend", ["Node.js", "React", "MongoDB"]),
                        ("UX Designer", "design", ["Figma", "UI/UX", "HTML/CSS"]),
                        ("API Engineer", "backend", ["Python", "FastAPI", "Redis"]),
                        ("Security Reviewer", "security", ["Cybersecurity", "Python", "Research"]),
                    ],
                ),
                (
                    "Climate resilience explorer",
                    "competition",
                    [
                        ("Computer Vision Researcher", "ml", ["Computer Vision", "PyTorch", "Python"]),
                        ("Data Storyteller", "data", ["Pandas", "Statistics", "Figma"]),
                        ("Research Coordinator", "research", ["Research", "Statistics", "Python"]),
                        ("Web Experience Designer", "design", ["Vue", "Figma", "UI/UX"]),
                    ],
                ),
                (
                    "Secure study network",
                    "startup",
                    [
                        ("Application Security Engineer", "security", ["Cybersecurity", "Docker", "Python"]),
                        ("Cloud Operations Engineer", "devops", ["AWS", "Kubernetes", "Docker"]),
                        ("Web Application Engineer", "frontend", ["React", "TypeScript", "Node.js"]),
                        ("Data Privacy Analyst", "research", ["Research", "SQL", "Cybersecurity"]),
                    ],
                ),
            ]

            for project_name, project_type, project_roles in demo_projects:
                cur.execute(
                    """
                    SELECT project_id FROM projects
                    WHERE owner_id = %s AND name = %s
                    """,
                    (user_ids[0], project_name),
                )
                project = cur.fetchone()
                if project is None:
                    cur.execute(
                        """
                        INSERT INTO projects (owner_id, name, project_type)
                        VALUES (%s, %s, %s)
                        RETURNING project_id
                        """,
                        (user_ids[0], project_name, project_type),
                    )
                    project_id = cur.fetchone()["project_id"]
                else:
                    project_id = project["project_id"]

                for title, role_type, required_skills in project_roles:
                    cur.execute(
                        """
                        SELECT role_id FROM project_roles
                        WHERE project_id = %s AND title = %s
                        """,
                        (project_id, title),
                    )
                    role = cur.fetchone()
                    if role is None:
                        cur.execute(
                            """
                            INSERT INTO project_roles (
                                project_id, title, role_type, slots_total, min_experience
                            )
                            VALUES (%s, %s, %s, 2, 1.0)
                            RETURNING role_id
                            """,
                            (project_id, title, role_type),
                        )
                        role_id = cur.fetchone()["role_id"]
                    else:
                        role_id = role["role_id"]

                    for skill in required_skills:
                        importance = 5 if skill == required_skills[0] else 3
                        cur.execute(
                            """
                            INSERT INTO role_skills (role_id, skill_id, importance)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (role_id, skill_id) DO NOTHING
                            """,
                            (role_id, skill_ids[skill], importance),
                        )

                cur.execute(
                    "SELECT milestone_id FROM milestones WHERE project_id = %s AND title = %s",
                    (project_id, "Prototype review"),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO milestones (project_id, title, due_at)
                        VALUES (%s, 'Prototype review', now() + interval '14 days')
                        """,
                        (project_id,),
                    )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.project_monthly_application_stats') "
                "AS view_name"
            )
            if cur.fetchone()["view_name"] is not None:
                cur.execute(
                    "REFRESH MATERIALIZED VIEW project_monthly_application_stats"
                )

    print("Seed complete: 250 diverse synthetic profiles, 5 projects, and 20 roles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SkillSync demo profiles and roles.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing application data before inserting the demo dataset.",
    )
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Skip seeding when the complete demo dataset already exists.",
    )
    args = parser.parse_args()
    main(reset=args.reset, if_missing=args.if_missing)
