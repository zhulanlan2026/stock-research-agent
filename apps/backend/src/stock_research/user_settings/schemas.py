from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSettingValueRequest(BaseModel):
    value: dict[str, object]


class UserSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: dict[str, object]
    updated_at: datetime
