from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """
    Request payload for user login.

    Rationale:
    - Login needs a stable user identifier, not necessarily a publicly deliverable email.
    - In internal systems, development environments often use non-public domains (e.g., *.local).
    - We therefore validate email as a non-empty string and normalize/validate further at the DB
    layer
      (unique constraint) and at the UI layer if needed.
    """

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """
    Response payload returned after a successful login.
    """

    access_token: str
    token_type: str
    expires_in: int
