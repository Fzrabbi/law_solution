import enum
from pydantic import BaseModel

class EntryType(enum.Enum):
  DILAM = "দিলাম"
  PELAM = "পেলাম"

class BookkeepingEntry(BaseModel):
  customer_name: str | None
  amount: int | None
  entry_type: EntryType | None
  notes: str | None

class InfoDeskReply(BaseModel):
  answer: str | None
  reference: int | None
  image: str | None

class CustomerSelection(BaseModel):
  selected_name: str | None
