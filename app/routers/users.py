"""User registration and login endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginResponse, UserCreate, UserLogin, UserRead
from app.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])

# Checked when the user doesn't exist, so a missing user takes about as long as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Create a user. The password is hashed before it is stored."""
    existing = db.scalars(
        select(User).where(or_(User.username == data.username, User.email == data.email))
    ).first()
    if existing is not None:  # LBYL: look for a duplicate before inserting
        field = "Username" if existing.username == data.username else "Email"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{field} already registered",
        )

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:  # EAFP: two requests can race past the check above, so the database has the last word
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Check the credentials. Wrong passwords and unknown users get the same response."""
    user = db.scalars(
        select(User).where(
            or_(User.username == data.username, User.email == data.username.lower())
        )
    ).first()
    # Always run one bcrypt check, so response time doesn't reveal whether the user exists.
    password_ok = verify_password(
        data.password, user.password_hash if user else _DUMMY_HASH
    )
    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return LoginResponse(message="Login successful", user=UserRead.model_validate(user))