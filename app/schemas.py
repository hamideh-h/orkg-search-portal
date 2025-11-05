from typing import List, Optional
from pydantic import BaseModel

class ResourceItem(BaseModel):
    id: str
    label: Optional[str] = None
    classes: List[str] = []

class SearchResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ResourceItem]
