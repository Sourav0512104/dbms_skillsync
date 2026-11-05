from contextlib import asynccontextmanager
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import psycopg

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_auth_settings,
    verify_password,
)
from .db import mongo, pg_conn, profiles
from .matching import hybrid_match
from .models import (
    ApplicationRequest,
    AuthResponse,
    LoginRequest,
    MatchRequest,
    ProfileUpdate,
    ProjectRoleCreate,
    RegisterRequest,
    UserSummary,
)
from .semantic import embed

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_auth_settings()
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_visible BOOLEAN "
                "NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_visible
                ON users(profile_visible)
                WHERE profile_visible = TRUE
                """
            )
    profiles.create_index("user_id", unique=True)
    yield
    mongo.close()


app = FastAPI(
    title="SkillSync API",
    description="Authenticated project and teammate discovery.",
    version="3.0.0",
    lifespan=lifespan,
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


def _auth_response(user: UserSummary) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.user_id), user=user)


@app.get("/health")
def health() -> dict[str, str]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()["version"]
    return {"status": "ok", "postgres": version.split(",")[0]}


@app.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(req: RegisterRequest) -> AuthResponse:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (full_name, email, password_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING user_id, full_name, email, availability_hours, experience_years
                """,
                (req.full_name.strip(), req.email, hash_password(req.password)),
            )
            user = cur.fetchone()
        conn.commit()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    profiles.insert_one(
        {
            "user_id": user["user_id"],
            "bio": "",
            "resume_text": "",
            "projects": [],
            "skills_text": [],
        }
    )
    return _auth_response(UserSummary(**user))


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, full_name, email, availability_hours,
                       experience_years, password_hash
                FROM users
                WHERE email = %s
                """,
                (req.email,),
            )
            user = cur.fetchone()

    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _auth_response(UserSummary(**user))


@app.get("/auth/me", response_model=UserSummary)
def read_current_user(
    current_user: UserSummary = Depends(get_current_user),
) -> UserSummary:
    return current_user


@app.get("/roles")
def roles(search: str | None = Query(default=None, max_length=120)) -> list[dict]:
    conditions = ["r.status = 'open'", "p.status = 'open'"]
    params: list[str] = []
    if search:
        conditions.append(
            """
            (
                r.title ILIKE %s
                OR p.name ILIKE %s
                OR EXISTS (
                    SELECT 1
                    FROM role_skills rs
                    JOIN skills s ON s.skill_id = rs.skill_id
                    WHERE rs.role_id = r.role_id
                      AND s.canonical_name ILIKE %s
                )
            )
            """
        )
        search_pattern = f"%{search.strip()}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT r.role_id, r.title, r.role_type, r.slots_total,
                       r.slots_filled, r.min_experience, r.status,
                       p.project_id, p.name AS project_name, p.project_type,
                       COALESCE(
                           array_agg(DISTINCT s.canonical_name)
                               FILTER (WHERE s.skill_id IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS skills
                FROM project_roles r
                JOIN projects p ON p.project_id = r.project_id
                LEFT JOIN role_skills rs ON rs.role_id = r.role_id
                LEFT JOIN skills s ON s.skill_id = rs.skill_id
                WHERE {" AND ".join(conditions)}
                GROUP BY r.role_id, p.project_id
                ORDER BY r.created_at DESC, r.role_id
                """,
                params,
            )
            return cur.fetchall()


@app.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    req: ProjectRoleCreate,
    current_user: UserSummary = Depends(get_current_user),
) -> dict[str, int | str]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects (owner_id, name, project_type)
                VALUES (%s, %s, %s)
                RETURNING project_id
                """,
                (current_user.user_id, req.project_name, req.project_type),
            )
            project_id = cur.fetchone()["project_id"]
            cur.execute(
                """
                INSERT INTO project_roles (
                    project_id, title, role_type, slots_total, min_experience
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING role_id
                """,
                (
                    project_id,
                    req.title,
                    req.role_type,
                    req.slots_total,
                    req.min_experience,
                ),
            )
            role_id = cur.fetchone()["role_id"]

            for skill in req.skills:
                cur.execute(
                    """
                    INSERT INTO skills (canonical_name, category)
                    VALUES (%s, %s)
                    ON CONFLICT (canonical_name) DO NOTHING
                    """,
                    (skill, req.role_type),
                )
                cur.execute(
                    "SELECT skill_id FROM skills WHERE canonical_name = %s",
                    (skill,),
                )
                skill_id = cur.fetchone()["skill_id"]
                cur.execute(
                    """
                    INSERT INTO role_skills (role_id, skill_id, importance)
                    VALUES (%s, %s, 3)
                    """,
                    (role_id, skill_id),
                )
        conn.commit()
    return {"status": "created", "project_id": project_id, "role_id": role_id}


@app.post("/match")
def match(
    req: MatchRequest,
    current_user: UserSummary = Depends(get_current_user),
) -> dict:
    try:
        result = hybrid_match(
            req.role_id,
            req.top_k,
            req.candidate_pool,
            req.rerank,
            excluded_user_id=current_user.user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    for candidate in result["matches"]:
        candidate.pop("user_id", None)
        candidate.pop("text", None)
    return result


@app.get("/profiles/me")
def read_profile(
    current_user: UserSummary = Depends(get_current_user),
) -> dict:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT profile_visible FROM users WHERE user_id = %s",
                (current_user.user_id,),
            )
            visibility = cur.fetchone()["profile_visible"]

    profile = profiles.find_one(
        {"user_id": current_user.user_id},
        {"_id": False, "embedding": False},
    ) or {}
    return {
        **profile,
        "user": current_user.model_dump(),
        "profile_visible": visibility,
        "skills": profile.get("skills_text", []),
    }


@app.put("/profiles/me")
def update_profile(
    req: ProfileUpdate,
    current_user: UserSummary = Depends(get_current_user),
) -> dict[str, str]:
    profile_text = " ".join(
        [req.bio, req.resume_text, " ".join(req.projects), " ".join(req.skills)]
    ).strip()
    vector = embed(profile_text)[0].tolist()
    normalized_skills = list(dict.fromkeys(skill.strip() for skill in req.skills))

    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET full_name = COALESCE(%s, full_name),
                    availability_hours = %s,
                    experience_years = %s,
                    profile_visible = %s
                WHERE user_id = %s
                """,
                (
                    req.full_name,
                    req.availability_hours,
                    req.experience_years,
                    req.profile_visible,
                    current_user.user_id,
                ),
            )
            cur.execute("DELETE FROM user_skills WHERE user_id = %s", (current_user.user_id,))
            skill_ids: list[int] = []
            for skill in normalized_skills:
                cur.execute(
                    """
                    INSERT INTO skills (canonical_name, category)
                    VALUES (%s, 'other')
                    ON CONFLICT (canonical_name) DO NOTHING
                    """,
                    (skill,),
                )
                cur.execute(
                    "SELECT skill_id FROM skills WHERE canonical_name = %s",
                    (skill,),
                )
                skill_ids.append(cur.fetchone()["skill_id"])
            if skill_ids:
                cur.executemany(
                    """
                    INSERT INTO user_skills (user_id, skill_id, proficiency, years_used)
                    VALUES (%s, %s, 3, 0)
                    """,
                    [(current_user.user_id, skill_id) for skill_id in skill_ids],
                )
        conn.commit()

    profiles.update_one(
        {"user_id": current_user.user_id},
        {
            "$set": {
                "user_id": current_user.user_id,
                "bio": req.bio,
                "resume_text": req.resume_text,
                "projects": req.projects,
                "skills_text": normalized_skills,
                "embedding": vector,
            }
        },
        upsert=True,
    )
    return {"status": "updated"}


@app.post("/applications", status_code=status.HTTP_201_CREATED)
def apply(
    req: ApplicationRequest,
    current_user: UserSummary = Depends(get_current_user),
) -> dict:
    try:
        with pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM apply_to_role(%s, %s)",
                    (current_user.user_id, req.role_id),
                )
                application = cur.fetchone()
            conn.commit()
        return {"status": "success", "application": application}
    except psycopg.Error as error:
        logger.exception("Application submission failed for user %s", current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The application could not be submitted. Check role availability and your existing applications.",
        ) from error


@app.get("/applications")
def list_applications(
    current_user: UserSummary = Depends(get_current_user),
) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.application_id, a.status, a.applied_at,
                       r.role_id, r.title AS role_title, r.role_type,
                       p.project_id, p.name AS project_name
                FROM applications a
                JOIN project_roles r ON r.role_id = a.role_id
                JOIN projects p ON p.project_id = r.project_id
                WHERE a.user_id = %s
                ORDER BY a.applied_at DESC
                """,
                (current_user.user_id,),
            )
            return cur.fetchall()


@app.get("/analytics/project-summary")
def project_summary(
    _: UserSummary = Depends(get_current_user),
) -> list[dict]:
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT project_id, name, total_applications, accepted, pending, rejected
                FROM project_application_summary
                ORDER BY total_applications DESC
                """
            )
            return cur.fetchall()
