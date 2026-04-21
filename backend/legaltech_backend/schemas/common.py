from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str
    version: str = Field(default="0.1.0")
