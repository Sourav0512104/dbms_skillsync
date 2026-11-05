from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Full name must contain at least two characters")
        return normalized

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return str(value).strip().lower()


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    email: str
    availability_hours: int
    experience_years: float


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class MatchRequest(BaseModel):
    role_id: int = Field(gt=0)
    top_k: int = Field(default=10, ge=1, le=50)
    candidate_pool: int = Field(default=50, ge=10, le=200)
    rerank: bool = True


class ApplicationRequest(BaseModel):
    role_id: int = Field(gt=0)


class ProjectRoleCreate(BaseModel):
    project_name: str = Field(min_length=2, max_length=160)
    project_type: Literal["hackathon", "lab", "startup", "research", "competition"]
    title: str = Field(min_length=2, max_length=160)
    role_type: Literal[
        "frontend", "backend", "ml", "data", "devops", "design",
        "security", "research", "other",
    ]
    slots_total: int = Field(default=2, ge=1, le=20)
    min_experience: float = Field(default=0, ge=0, le=70)
    skills: list[Annotated[str, Field(max_length=80)]] = Field(
        min_length=1,
        max_length=20,
    )

    @field_validator("project_name", "title")
    @classmethod
    def clean_names(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Names must contain at least two characters")
        return normalized

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not cleaned:
            raise ValueError("Add at least one required skill")
        return cleaned


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    bio: str = Field(default="", max_length=5000)
    resume_text: str = Field(default="", max_length=20000)
    projects: list[str] = Field(default_factory=list, max_length=30)
    skills: list[str] = Field(default_factory=list, max_length=50)
    availability_hours: int = Field(default=10, ge=0, le=80)
    experience_years: float = Field(default=0, ge=0, le=70)
    profile_visible: bool = False

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Full name must contain at least two characters")
        return normalized

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))

    @field_validator("projects")
    @classmethod
    def clean_projects(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class ProjectContextCreate(BaseModel):
    project_id: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=10000)
    required_technologies: list[str] = Field(default_factory=list, max_length=50)
