import os
import re
import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, Field, field_validator

from backend.database.mongodb import get_db
from backend.database.collections import serialize_doc

logger = logging.getLogger("traingpt.auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Security and hashing setup
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_traingpt_key_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Email format check regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = get_db()
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return serialize_doc(user)


# Pydantic validation schemas
class UserRegister(BaseModel):
    name: str = Field(..., min_length=1)
    email: str
    password: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("confirmPassword")
    @classmethod
    def passwords_match(cls, v, info):
        password = info.data.get("password")
        if password is not None and v != password:
            raise ValueError("Passwords do not match")
        return v

class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str = "user"
    provider: str = "local"
    createdAt: str
    lastLogin: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class SocialLoginRequest(BaseModel):
    token: str
    email: Optional[str] = None
    name: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v.lower()

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)

    @field_validator("confirmPassword")
    @classmethod
    def passwords_match(cls, v, info):
        password = info.data.get("newPassword")
        if password is not None and v != password:
            raise ValueError("Passwords do not match")
        return v


# Route Handlers
@router.post("/register", response_model=TokenResponse)
async def register(user_in: UserRegister):
    db = get_db()
    existing = await db.users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
    
    pw_hash = hash_password(user_in.password)
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "name": user_in.name,
        "email": user_in.email,
        "password": pw_hash,
        "provider": "local",
        "role": "user",
        "createdAt": now,
        "lastLogin": now
    }
    
    res = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(res.inserted_id)
    serialized = serialize_doc(user_doc)
    
    token = create_access_token({"sub": user_doc["email"]})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": serialized["_id"],
            "name": serialized["name"],
            "email": serialized["email"],
            "role": serialized["role"],
            "provider": serialized["provider"],
            "createdAt": serialized["createdAt"],
            "lastLogin": serialized["lastLogin"]
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    db = get_db()
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    
    if user.get("provider") != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please sign in using your {user.get('provider')} account"
        )
    
    if not verify_password(credentials.password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
        
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"lastLogin": now}})
    user["lastLogin"] = now
    
    serialized = serialize_doc(user)
    token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": serialized["_id"],
            "name": serialized["name"],
            "email": serialized["email"],
            "role": serialized["role"],
            "provider": serialized["provider"],
            "createdAt": serialized["createdAt"],
            "lastLogin": serialized["lastLogin"]
        }
    }

@router.post("/google", response_model=TokenResponse)
async def google_login(payload: SocialLoginRequest):
    email = payload.email
    name = payload.name or "Google User"
    
    if not email:
        if payload.token.startswith("mock_"):
            parts = payload.token.split("_")
            email = parts[-1] if len(parts) > 1 and "@" in parts[-1] else "google_user@example.com"
        else:
            email = "google_user@example.com"
            
    db = get_db()
    user = await db.users.find_one({"email": email})
    now = datetime.now(timezone.utc).isoformat()
    
    if not user:
        user_doc = {
            "name": name,
            "email": email,
            "password": "",
            "provider": "google",
            "role": "user",
            "createdAt": now,
            "lastLogin": now
        }
        res = await db.users.insert_one(user_doc)
        user_doc["_id"] = str(res.inserted_id)
        user = user_doc
    else:
        if user.get("provider") != "google":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This email is already registered with {user.get('provider')}"
            )
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"lastLogin": now}})
        user["lastLogin"] = now
        
    serialized = serialize_doc(user)
    token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": serialized["_id"],
            "name": serialized["name"],
            "email": serialized["email"],
            "role": serialized["role"],
            "provider": serialized["provider"],
            "createdAt": serialized["createdAt"],
            "lastLogin": serialized["lastLogin"]
        }
    }

@router.post("/github", response_model=TokenResponse)
async def github_login(payload: SocialLoginRequest):
    email = payload.email
    name = payload.name or "GitHub User"
    
    if not email:
        if payload.token.startswith("mock_"):
            parts = payload.token.split("_")
            email = parts[-1] if len(parts) > 1 and "@" in parts[-1] else "github_user@example.com"
        else:
            email = "github_user@example.com"
            
    db = get_db()
    user = await db.users.find_one({"email": email})
    now = datetime.now(timezone.utc).isoformat()
    
    if not user:
        user_doc = {
            "name": name,
            "email": email,
            "password": "",
            "provider": "github",
            "role": "user",
            "createdAt": now,
            "lastLogin": now
        }
        res = await db.users.insert_one(user_doc)
        user_doc["_id"] = str(res.inserted_id)
        user = user_doc
    else:
        if user.get("provider") != "github":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This email is already registered with {user.get('provider')}"
            )
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"lastLogin": now}})
        user["lastLogin"] = now
        
    serialized = serialize_doc(user)
    token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": serialized["_id"],
            "name": serialized["name"],
            "email": serialized["email"],
            "role": serialized["role"],
            "provider": serialized["provider"],
            "createdAt": serialized["createdAt"],
            "lastLogin": serialized["lastLogin"]
        }
    }

@router.post("/guest", response_model=TokenResponse)
async def guest_login():
    db = get_db()
    guest_id = str(uuid.uuid4())[:8]
    email = f"guest_{guest_id}@traingpt.ai"
    name = f"Guest_{guest_id}"
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "name": name,
        "email": email,
        "password": "",
        "provider": "guest",
        "role": "guest",
        "createdAt": now,
        "lastLogin": now
    }
    
    res = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(res.inserted_id)
    serialized = serialize_doc(user_doc)
    
    token = create_access_token({"sub": email}, expires_delta=timedelta(minutes=15))
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": serialized["_id"],
            "name": serialized["name"],
            "email": serialized["email"],
            "role": serialized["role"],
            "provider": serialized["provider"],
            "createdAt": serialized["createdAt"],
            "lastLogin": serialized["lastLogin"]
        }
    }

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "provider": current_user.get("provider", "local"),
        "createdAt": current_user.get("createdAt", current_user.get("created_at", "")),
        "lastLogin": current_user.get("lastLogin")
    }

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"status": "success", "message": "Successfully logged out"}

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    db = get_db()
    user = await db.users.find_one({"email": payload.email})
    if not user:
        return {"status": "success", "message": "If this email exists, a reset link has been sent"}
        
    if user.get("provider") != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset password for social login accounts"
        )
        
    reset_token = secrets.token_urlsafe(32)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    
    await db.reset_tokens.update_one(
        {"email": payload.email},
        {"$set": {"token": reset_token, "expiry": expiry}},
        upsert=True
    )
    
    logger.info(f"PASSWORD RESET LINK for {payload.email}: http://localhost:5173/reset-password?token={reset_token}")
    
    return {"status": "success", "message": "Password reset link generated"}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    db = get_db()
    token_doc = await db.reset_tokens.find_one({"token": payload.token})
    if not token_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
        
    expiry = datetime.fromisoformat(token_doc["expiry"])
    if datetime.now(timezone.utc) > expiry:
        await db.reset_tokens.delete_one({"token": payload.token})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
        
    email = token_doc["email"]
    pw_hash = hash_password(payload.newPassword)
    
    await db.users.update_one({"email": email}, {"$set": {"password": pw_hash}})
    await db.reset_tokens.delete_one({"token": payload.token})
    
    return {"status": "success", "message": "Password has been reset successfully"}
