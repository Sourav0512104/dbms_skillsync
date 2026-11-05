from .db import pg_conn, profiles
from .semantic import cosine, embed, rerank


def load_role(role_id: int) -> dict:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, p.name AS project_name, p.project_type
                FROM project_roles r
                JOIN projects p ON p.project_id = r.project_id
                WHERE r.role_id = %s
                """,
                (role_id,),
            )
            role = cur.fetchone()
            if not role:
                raise ValueError("Role not found")

            cur.execute(
                """
                SELECT s.canonical_name, rs.importance
                FROM role_skills rs
                JOIN skills s ON s.skill_id = rs.skill_id
                WHERE rs.role_id = %s
                ORDER BY rs.importance DESC, s.canonical_name
                """,
                (role_id,),
            )
            role["skills"] = cur.fetchall()
            return role


def role_text(role: dict) -> str:
    skills = ", ".join(
        f"{skill['canonical_name']} (importance {skill['importance']}/5)"
        for skill in role["skills"]
    )
    return (
        f"Role: {role['title']}. Type: {role['role_type']}. "
        f"Minimum experience: {role['min_experience']} years. "
        f"Required skills: {skills}."
    )


def structured_candidates(
    role: dict,
    limit: int,
    excluded_user_id: int | None = None,
) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.availability_hours,
                       u.experience_years,
                       COALESCE(
                           array_agg(s.canonical_name)
                               FILTER (WHERE s.skill_id IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS skills
                FROM users u
                LEFT JOIN user_skills us ON us.user_id = u.user_id
                LEFT JOIN skills s ON s.skill_id = us.skill_id
                WHERE u.profile_visible = TRUE
                  AND u.user_id <> COALESCE(%s, -1)
                  AND u.availability_hours >= 5
                  AND u.experience_years >= %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM applications a
                      WHERE a.user_id = u.user_id
                        AND a.role_id = %s
                        AND a.status IN ('pending', 'accepted')
                  )
                GROUP BY u.user_id
                ORDER BY u.experience_years DESC
                LIMIT %s
                """,
                (
                    excluded_user_id,
                    role["min_experience"],
                    role["role_id"],
                    limit,
                ),
            )
            return cur.fetchall()


def candidate_document(user_id: int) -> dict:
    return profiles.find_one({"user_id": user_id}) or {
        "user_id": user_id,
        "bio": "",
        "resume_text": "",
        "projects": [],
        "embedding": None,
    }


def hybrid_match(
    role_id: int,
    top_k: int = 10,
    candidate_pool: int = 50,
    do_rerank: bool = True,
    excluded_user_id: int | None = None,
) -> dict:
    role = load_role(role_id)
    candidates = structured_candidates(role, candidate_pool, excluded_user_id)
    query = role_text(role)
    query_vector = embed(query)[0]
    scored = []

    required_skills = {
        skill["canonical_name"].lower()
        for skill in role["skills"]
    }

    for candidate in candidates:
        document = candidate_document(candidate["user_id"])
        text = " ".join(
            [
                document.get("bio", ""),
                document.get("resume_text", ""),
                " ".join(document.get("projects", [])),
                " ".join(candidate.get("skills", [])),
            ]
        ).strip()
        document_vector = document.get("embedding")
        if document_vector is None:
            document_vector = embed(text)[0].tolist()
            profiles.update_one(
                {"user_id": candidate["user_id"]},
                {"$set": {"embedding": document_vector}},
                upsert=True,
            )

        candidate_skills = {
            skill.lower() for skill in candidate.get("skills", [])
        }
        skill_overlap = len(required_skills & candidate_skills) / max(
            1,
            len(required_skills),
        )
        experience = float(candidate["experience_years"])
        availability = candidate["availability_hours"]
        experience_score = min(
            1.0,
            experience / max(1.0, float(role["min_experience"]) + 2),
        )
        availability_score = min(1.0, float(availability) / 20.0)

        scored.append(
            {
                "user_id": candidate["user_id"],
                "name": candidate["full_name"],
                "semantic_score": cosine(query_vector, document_vector),
                "skill_overlap": skill_overlap,
                "experience_score": experience_score,
                "availability_score": availability_score,
                "text": text,
                "skills": candidate.get("skills", []),
                "experience_years": experience,
                "availability_hours": availability,
            }
        )

    scored.sort(key=lambda candidate: candidate["semantic_score"], reverse=True)
    shortlist = scored[:candidate_pool]
    reranker_scores = (
        rerank(query, [candidate["text"] for candidate in shortlist])
        if do_rerank and shortlist
        else [candidate["semantic_score"] for candidate in shortlist]
    )

    for candidate, score in zip(shortlist, reranker_scores):
        candidate["reranker_score"] = score

    values = [candidate["reranker_score"] for candidate in shortlist]
    lowest = min(values, default=0)
    highest = max(values, default=1)

    for candidate in shortlist:
        reranker_normalized = (
            (candidate["reranker_score"] - lowest) / (highest - lowest + 1e-9)
            if highest > lowest
            else 0.5
        )
        candidate["final_score"] = (
            0.55 * reranker_normalized
            + 0.25 * candidate["skill_overlap"]
            + 0.10 * candidate["experience_score"]
            + 0.10 * candidate["availability_score"]
        )
        candidate["explanation"] = {
            "reranker": 0.55,
            "skill_overlap": 0.25,
            "experience": 0.10,
            "availability": 0.10,
        }

    shortlist.sort(key=lambda candidate: candidate["final_score"], reverse=True)
    return {
        "role": role,
        "query": query,
        "matches": shortlist[:top_k],
    }
