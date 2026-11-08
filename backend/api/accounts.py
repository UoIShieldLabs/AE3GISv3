"""Sign-in, sign-up and the caller's own account (``/api/v1/auth``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from api.deps import get_db, get_settings
from api.schemas import LoginIn, MeOut, PasswordChangeIn, SessionOut, SignupIn, UserOut
from auth import WEBUI_COOKIE, WEBUI_COOKIE_PATH, current_identity, parse_bearer
from config import Settings
from services import accounts
from services.accounts import Identity, SignIn

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _user_out(identity: Identity) -> UserOut:
    return UserOut(id=identity.user_id, username=identity.username, role=identity.role)


def _session_out(sign_in: SignIn) -> SessionOut:
    return SessionOut(
        token=sign_in.token,
        expires_at=sign_in.expires_at,
        user=_user_out(accounts.identity_of(sign_in.user)),
    )


@router.post("/login", response_model=SessionOut)
def login(
    body: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Sign in. 401 ``bad_credentials``; 429 ``too_many_attempts`` after
    repeated failures; 409 ``accounts_off`` when the instance has no accounts."""
    client = request.client.host if request.client else ""
    sign_in = accounts.login(
        db,
        settings,
        request.app.state.login_limiter,
        username=body.username,
        password=body.password,
        client=client,
    )
    return _session_out(sign_in)


@router.post("/signup", response_model=SessionOut, status_code=201)
def signup(
    body: SignupIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Create a student account with the class join code, and sign in.
    403 ``signup_closed`` / ``bad_join_code``; 409 ``username_taken``;
    422 ``invalid_username`` / ``weak_password``."""
    sign_in = accounts.signup(
        db, settings, username=body.username, password=body.password, join_code=body.join_code
    )
    return _session_out(sign_in)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """End this sign-in (a no-op for an unknown token)."""
    accounts.end_session(db, parse_bearer(authorization))
    response.delete_cookie(WEBUI_COOKIE, path=WEBUI_COOKIE_PATH)
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
def me(identity: Identity = Depends(current_identity), settings: Settings = Depends(get_settings)):
    return MeOut(user=_user_out(identity), auth_required=settings.auth_required)


@router.post("/password", status_code=204)
def change_password(
    body: PasswordChangeIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """Change your own password; your other sign-ins end. The instructor's is
    set by the environment (409 ``managed_by_env``)."""
    accounts.change_password(
        db, identity, current=body.current, new=body.new, keep_token=parse_bearer(authorization)
    )
    return Response(status_code=204)


@router.post("/webui-cookie", status_code=204)
def webui_cookie(
    response: Response,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    _: Identity = Depends(current_identity),
):
    """Let the node web-UI relay's iframe pages authenticate: they cannot send
    a header, so this sign-in's token goes into an HttpOnly, SameSite=Strict
    cookie that only the relay routes accept. Call it before opening one."""
    token = parse_bearer(authorization)
    if settings.auth_required and token:
        response.set_cookie(
            WEBUI_COOKIE,
            token,
            path=WEBUI_COOKIE_PATH,
            httponly=True,
            samesite="strict",
            max_age=int(settings.session_ttl_hours * 3600),
        )
    response.status_code = 204
    return response
