import re
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InterviewBooking
from app.schemas.booking import BookingResponse, BookingSlots

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REQUIRED_FIELDS = ("name", "email", "interview_date", "interview_time")


class BookingService:
    @staticmethod
    def merge_slots(existing: dict[str, str | None], extracted: BookingSlots) -> dict[str, str | None]:
        merged = dict(existing)
        for field, value in extracted.model_dump().items():
            if value:
                merged[field] = value
        return merged

    @staticmethod
    def missing_fields(slots: dict[str, str | None]) -> list[str]:
        return [field for field in _REQUIRED_FIELDS if not slots.get(field)]

    @staticmethod
    def validate_slots(slots: dict[str, str | None]) -> list[str]:
        errors: list[str] = []
        email = slots.get("email")
        if email and not _EMAIL_PATTERN.match(email):
            errors.append(f"'{email}' is not a valid email address")

        interview_date = slots.get("interview_date")
        if interview_date:
            try:
                _parse_date(interview_date)
            except ValueError:
                errors.append(f"'{interview_date}' is not a valid date (expected YYYY-MM-DD)")

        interview_time = slots.get("interview_time")
        if interview_time:
            try:
                _parse_time(interview_time)
            except ValueError:
                errors.append(f"'{interview_time}' is not a valid time (expected HH:MM)")

        return errors

    @staticmethod
    def is_slot_taken(db: Session, interview_date: str, interview_time: str) -> bool:
        stmt = select(InterviewBooking).where(
            InterviewBooking.interview_date == _parse_date(interview_date),
            InterviewBooking.interview_time == _parse_time(interview_time),
        )
        return db.scalars(stmt).first() is not None

    @staticmethod
    def create_booking(db: Session, session_id: str, slots: dict[str, str | None]) -> BookingResponse:
        booking = InterviewBooking(
            session_id=session_id,
            name=slots["name"],
            email=slots["email"],
            interview_date=_parse_date(slots["interview_date"]),
            interview_time=_parse_time(slots["interview_time"]),
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return BookingResponse.model_validate(booking)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()
