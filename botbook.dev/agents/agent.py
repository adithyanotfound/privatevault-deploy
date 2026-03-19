from pydantic import BaseModel
from typing import List, Optional

class Agent(BaseModel):
    name: str
    description: str
    capabilities: List[str]
    owner: str
    verified: Optional[bool] = False
