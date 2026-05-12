from pydantic import BaseModel, Field


class WorkflowCreateRequest(BaseModel):
    objective: str = Field(min_length=5)


class WorkflowCreateResponse(BaseModel):
    thread_id: str
    status: str
