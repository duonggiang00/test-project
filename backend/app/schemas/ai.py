from pydantic import BaseModel, ConfigDict
import uuid

class ProcessDocumentRequest(BaseModel):
    material_id: uuid.UUID

class ProcessDocumentResponse(BaseModel):
    message: str
    chunks_created: int

    model_config = ConfigDict(from_attributes=True)
