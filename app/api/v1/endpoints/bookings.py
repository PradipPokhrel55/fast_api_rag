from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InterviewBooking
from app.db.session import get_db
from app.schemas.booking import BookingResponse

router = APIRouter(prefix="/bookings", tags=["Interview Bookings"])


@router.get("", response_model=list[BookingResponse])
def list_bookings(db: Session = Depends(get_db)) -> list[InterviewBooking]:
    return list(db.scalars(select(InterviewBooking).order_by(InterviewBooking.created_at.desc())))


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: str, db: Session = Depends(get_db)) -> InterviewBooking:
    booking = db.get(InterviewBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking
