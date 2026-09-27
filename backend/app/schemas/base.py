from pydantic import BaseModel, ConfigDict


class TracevaBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
