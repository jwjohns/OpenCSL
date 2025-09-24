from pydantic import BaseModel
from typing import List, Optional

class Metric(BaseModel):
    name: str
    definition: str
    filters: Optional[List[str]] = []
    owner: Optional[str] = None
    tags: Optional[List[str]] = []

class Dimension(BaseModel):
    name: str
    definition: str
    hierarchy: Optional[List[str]] = []