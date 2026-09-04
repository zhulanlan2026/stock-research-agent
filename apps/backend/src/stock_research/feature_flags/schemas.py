import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

TENANT_ALLOWLIST = "tenant_allowlist"
USER_ALLOWLIST = "user_allowlist"


class FeatureFlagCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    environment: str = Field(default="production", max_length=50)
    enabled: bool = False
    percentage: int = Field(default=0, ge=0, le=100)
    kill_switch: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None


class FeatureFlagRuleCreate(BaseModel):
    rule_type: str = Field(pattern=f"^({TENANT_ALLOWLIST}|{USER_ALLOWLIST})$")
    rule_value: str = Field(min_length=1, max_length=200)


class FeatureFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    environment: str
    enabled: bool
    percentage: int
    kill_switch: bool
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime
