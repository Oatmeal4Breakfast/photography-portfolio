from pydantic import BaseModel
from typing import List


class DeletePhotoPayload(BaseModel):
    photo_ids: List[int]
