from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TracevaBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(TracevaBaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(TracevaBaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    facility_id: int | None = None
    ward_id: int | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    facility_name: str | None = None
    ward_name: str | None = None


class TokenResponse(TracevaBaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(TracevaBaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str
    facility_id: int | None = None
    ward_id: int | None = None
    status: str = "ACTIVE"


class UserUpdate(TracevaBaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: str | None = None
    facility_id: int | None = None
    ward_id: int | None = None
    status: str | None = None


class FacilityResponse(TracevaBaseModel):
    id: int
    name: str
    type: str
    address: str | None = None
    contact: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str = "ACTIVE"
    created_at: str | None = None
    ward_count: int | None = None


class FacilityCreate(TracevaBaseModel):
    name: str = Field(..., min_length=2)
    type: str = "Hospital"
    address: str | None = None
    contact: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str = "ACTIVE"


class FacilityUpdate(TracevaBaseModel):
    name: str | None = None
    type: str | None = None
    address: str | None = None
    contact: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None


class WardResponse(TracevaBaseModel):
    id: int
    facility_id: int
    name: str
    department_type: str
    manager_user_id: int | None = None
    created_at: str | None = None


class WardCreate(TracevaBaseModel):
    facility_id: int
    name: str = Field(..., min_length=2)
    department_type: str = "General"
    manager_user_id: int | None = None


class WardUpdate(TracevaBaseModel):
    facility_id: int | None = None
    name: str | None = None
    department_type: str | None = None
    manager_user_id: int | None = None


class MessageResponse(TracevaBaseModel):
    message: str
