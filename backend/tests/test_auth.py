import os
import unittest
from unittest.mock import patch

os.environ["JWT_SECRET_KEY"] = "focused-auth-test-secret-0123456789"

import jwt
from pydantic import ValidationError

from app.auth import create_access_token, hash_password, verify_password
from app.models import ProfileUpdate, ProjectRoleCreate, RegisterRequest


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_verifies_only_the_original_password(self) -> None:
        stored_hash = hash_password("a-long-test-password")

        self.assertNotEqual(stored_hash, "a-long-test-password")
        self.assertTrue(verify_password("a-long-test-password", stored_hash))
        self.assertFalse(verify_password("another-password", stored_hash))
        self.assertFalse(verify_password("anything", None))

    def test_access_token_has_user_subject_and_expiration(self) -> None:
        token = create_access_token(42)
        claims = jwt.decode(
            token,
            os.environ["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )

        self.assertEqual(claims["sub"], "42")
        self.assertIn("exp", claims)

    def test_short_jwt_secret_is_rejected(self) -> None:
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "too-short"}):
            with self.assertRaises(RuntimeError):
                create_access_token(42)


class AccountModelTests(unittest.TestCase):
    def test_registration_normalizes_email(self) -> None:
        request = RegisterRequest(
            full_name="  Ada Lovelace ",
            email="  ADA@example.com ",
            password="long-enough-password",
        )

        self.assertEqual(request.full_name, "Ada Lovelace")
        self.assertEqual(request.email, "ada@example.com")

    def test_registration_rejects_invalid_email_and_short_password(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(
                full_name="Ada Lovelace",
                email="not-an-email",
                password="long-enough-password",
            )
        with self.assertRaises(ValidationError):
            RegisterRequest(
                full_name="Ada Lovelace",
                email="ada@example.com",
                password="short",
            )

    def test_new_profiles_are_private_and_skills_are_normalized(self) -> None:
        profile = ProfileUpdate(skills=[" Python ", "Python", ""])

        self.assertFalse(profile.profile_visible)
        self.assertEqual(profile.skills, ["Python"])
        self.assertEqual(profile.projects, [])


class ProjectRoleModelTests(unittest.TestCase):
    def test_role_request_normalizes_names_and_required_skills(self) -> None:
        role = ProjectRoleCreate(
            project_name="  Campus helper ",
            project_type="lab",
            title="  Backend engineer ",
            role_type="backend",
            skills=[" Python ", "FastAPI", "Python", ""],
        )

        self.assertEqual(role.project_name, "Campus helper")
        self.assertEqual(role.title, "Backend engineer")
        self.assertEqual(role.skills, ["Python", "FastAPI"])

    def test_role_request_requires_supported_project_and_role_types(self) -> None:
        with self.assertRaises(ValidationError):
            ProjectRoleCreate(
                project_name="Campus helper",
                project_type="community",
                title="Backend engineer",
                role_type="backend",
                skills=["Python"],
            )

        with self.assertRaises(ValidationError):
            ProjectRoleCreate(
                project_name="Campus helper",
                project_type="lab",
                title="Backend engineer",
                role_type="product",
                skills=["Python"],
            )

        with self.assertRaises(ValidationError):
            ProjectRoleCreate(
                project_name="Campus helper",
                project_type="lab",
                title="Backend engineer",
                role_type="backend",
                skills=["", " "],
            )

        with self.assertRaises(ValidationError):
            ProjectRoleCreate(
                project_name="Campus helper",
                project_type="lab",
                title="Backend engineer",
                role_type="backend",
                skills=["x" * 81],
            )


if __name__ == "__main__":
    unittest.main()
