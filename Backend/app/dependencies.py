from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user

    return role_checker


RequireSME = Annotated[User, Depends(require_roles(UserRole.SME))]
RequireLender = Annotated[User, Depends(require_roles(UserRole.LENDER))]
RequireAdmin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
RequireSubAdmin = Annotated[User, Depends(require_roles(UserRole.SUBADMIN))]
RequireAdminOrSubAdmin = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUBADMIN))]
RequireLenderOrAdmin = Annotated[User, Depends(require_roles(UserRole.LENDER, UserRole.ADMIN, UserRole.SUBADMIN))]
