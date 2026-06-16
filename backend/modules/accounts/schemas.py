from pydantic import BaseModel, Field
from datetime import datetime

class SignupRequest(BaseModel):
    email: str
    password: str

class SignupResult(BaseModel):
    account_id: str = Field(..., serialization_alias="accountId")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "accountId": "a0000000-0000-0000-0000-000000000000"
            }
        }

class LoginRequest(BaseModel):
    email: str
    password: str

class SessionInfo(BaseModel):
    user_id: str = Field(..., serialization_alias="userId")
    expires_at: datetime = Field(..., serialization_alias="expiresAt")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "userId": "a0000000-0000-0000-0000-000000000000",
                "expiresAt": "2026-07-16T18:00:00Z"
            }
        }

class ValidationErrorDTO(BaseModel):
    field: str | None = None
    message: str
