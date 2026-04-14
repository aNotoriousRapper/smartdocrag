from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from src.smartdocrag.core.config import settings
from src.smartdocrag.core.database import get_db
from src.smartdocrag.auth.crud import create_user, authenticate_user, get_user_by_username
from src.smartdocrag.auth.utils import create_access_token
from src.smartdocrag.auth.schemas import Token, UserCreate

auth_router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@auth_router.post("/register", response_model=Token)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    # 检查用户名是否已存在
    existing_user = await get_user_by_username(db, user_create.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建新用户
    user = await create_user(
        db=db,
        username=user_create.username,
        password=user_create.password,
        email=getattr(user_create, 'email', None),
        full_name=getattr(user_create, 'full_name', None)
    )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}