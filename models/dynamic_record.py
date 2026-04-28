# models/dynamic_record.py
from pydantic import BaseModel
from typing import Any
import math

class DynamicRecord(BaseModel):
    data: dict[str, Any]
    row_index: int = 0
    source_file: str = ""

    def to_prompt_text(self) -> str:
        lines = []
        for key, value in self.data.items():
            # Ignore None
            if value is None:
                continue
            # Ignore NaN (float)
            if isinstance(value, float) and math.isnan(value):
                continue
            # Ignore NaN (string)
            if str(value).lower().strip() in ["nan", "none", "null", ""]:
                continue
            text = str(value)
            if len(text) > 200:
                text = text[:200] + "…[tronqué]"
            lines.append(f"  {key}: {text}")
        return "\n".join(lines)

    class Config:
        extra = "ignore"