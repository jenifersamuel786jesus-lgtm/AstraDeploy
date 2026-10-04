from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.entities import AppSession, Membership, User

COOKIE_NAME = "webdev_app_session"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _preview_identity(token: str) -> str | None:
    secret = os.getenv("MANUS_JWT_SECRET")
    app_id = os.getenv("MANUS_PROJECT_ID")
    if not secret or not app_id:
        return None
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp"]})
        if claims.get("appId") != app_id:
            return None
        identity = claims.get("openId") or claims.get("openid") or claims.get("sub")
        return str(identity) if identity else None
    except jwt.PyJWTError:
        return None


def ensure_user_and_org(db: Session, *, open_id: str, email: str | None, name: str) -> tuple[User, Membership]:
    user = db.scalar(select(User).where(User.open_id == open_id))
    if user is None:
        user = User(open_id=open_id, email=email, name=(name or "AstraDeploy user")[:180])
        db.add(user)
        db.flush()
    elif email and not user.email:
        user.email = email[:320]
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at))
    if membership is None:
        from backend.app.models.entities import Organization, Project
        organization = Organization(name=f"{user.name.split()[0]}'s workspace")
        db.add(organization)
        db.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id, role="Admin")
        db.add(membership)
        db.add(Project(organization_id=organization.id, name="ML Platform", description="Default AstraDeploy project"))
        db.flush()
        from backend.app.services.seed import seed_demo_workspace
        seed_demo_workspace(db, organization.id)
    db.commit()
    db.refresh(user)
    db.refresh(membership)
    return user, membership


def resolve_user(request: Request, db: Session) -> tuple[User, Membership]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in with your organization account to continue.")
    stored = db.get(AppSession, _hash_token(token))
    if stored:
        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            user = db.get(User, stored.user_id)
            membership = db.scalar(select(Membership).where(Membership.user_id == stored.user_id).order_by(Membership.created_at))
            if user and membership:
                return user, membership
    open_id = _preview_identity(token)
    if open_id:
        user, membership = ensure_user_and_org(db, open_id=open_id, email=None, name="AstraDeploy member")
        return user, membership
    raise HTTPException(status_code=401, detail="Your session is invalid or expired. Please sign in again.")


def create_session(db: Session, user: User) -> str:
    import secrets
    token = secrets.token_urlsafe(40)
    db.add(AppSession(id=_hash_token(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=14)))
    db.commit()
    return token


def current_context(request: Request, db: Session) -> dict[str, Any]:
    user, membership = resolve_user(request, db)
    return {
        "user": user,
        "membership": membership,
        "organization_id": membership.organization_id,
        "role": membership.role,
    }


def require_roles(context: dict[str, Any], allowed: set[str]) -> None:
    if context["role"] not in allowed:
        raise HTTPException(status_code=403, detail="Your organization role cannot perform this action.")


def cookie_secure(request: Request) -> bool:
    # Only an explicit local HTTP setting relaxes Secure; public Preview stays Secure even
    # when the reverse proxy connects to the app over HTTP.
    local_http = os.getenv("ASTRA_LOCAL_HTTP_COOKIES", "false").lower() == "true"
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(":", 1)[0]
    return not (local_http and host in {"localhost", "127.0.0.1"})
