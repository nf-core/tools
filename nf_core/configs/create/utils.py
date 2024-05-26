from typing import Optional

from pydantic import BaseModel


class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    config_type: Optional[str] = None
