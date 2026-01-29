"""User management routes including registration."""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_db
from models.postgres import User
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class UserRegister(BaseModel):
    """Request body for user registration."""

    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response body for user operations."""

    id: str
    email: str
    name: str | None


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user.

    Creates a new user with the provided email and password.
    Password is hashed using bcrypt before storage.
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists",
        )

    # Hash the password
    password_hash = bcrypt.hashpw(
        user_data.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        name=user_data.name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"New user registered: {user_data.email}")

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
    )


@router.post("/login", response_model=UserResponse)
async def login_user(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user.

    Validates email and password against the database.
    Returns user data if credentials are valid.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Verify password
    if not bcrypt.checkpw(
        user_data.password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    logger.info(f"User logged in: {user_data.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
    )
