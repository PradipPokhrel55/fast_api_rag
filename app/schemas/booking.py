from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class BookingSlots(BaseModel):
    name: str | None = None
    email: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    name: str
    email: str
    interview_date: date
    interview_time: time
    status: str
    created_at: datetime
