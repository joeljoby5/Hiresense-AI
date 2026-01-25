from fastapi import APIRouter, Request, Response
from pydantic import EmailStr, Field

from app.api.session_security import cookie_name, require_csrf, require_origin, secure_cookie, session_token
from app.schemas.resumes import RequestModel
from app.services.accounts import AccountState, SESSION_SECONDS, SignIn
from app.services.errors import AuthenticationRequired


class Credentials(RequestModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class Registration(Credentials):
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="", max_length=120)


class ProfileRequest(RequestModel):
    display_name: str = Field(max_length=120)


class PasswordChange(RequestModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class DeleteAccount(RequestModel):
    password: str = Field(min_length=1, max_length=256)


router = APIRouter(prefix="/auth", tags=["Accounts"])


def _session(request: Request, mutate: bool = False) -> str:
    token = session_token(request)
    if token is None:
        raise AuthenticationRequired()
    if mutate:
        require_csrf(request, token)
    return token


def _budget(request: Request) -> None:
    request.app.state.login_attempts.check(request.client.host if request.client else "unknown")


def _signed(request: Request, response: Response, result: SignIn) -> AccountState:
    response.set_cookie(cookie_name(request), result.token, httponly=True, secure=secure_cookie(request),
                        samesite="strict", path="/", max_age=SESSION_SECONDS)
    response.headers["Cache-Control"] = "private, no-store"
    return result.state


def _clear(request: Request):
    response = Response(status_code=204, headers={"Cache-Control": "private, no-store"})
    response.delete_cookie(cookie_name(request), path="/", secure=secure_cookie(request), httponly=True, samesite="strict")
    return response


@router.post("/register", status_code=201, response_model=AccountState)
def register(body: Registration, request: Request, response: Response):
    require_origin(request)
    _budget(request)
    result = request.app.state.accounts.register(body.email.casefold(), body.password, body.display_name.strip(), session_token(request))
    return _signed(request, response, result)


@router.post("/login", response_model=AccountState)
def login(body: Credentials, request: Request, response: Response):
    require_origin(request)
    _budget(request)
    result = request.app.state.accounts.login(body.email.casefold(), body.password, session_token(request))
    return _signed(request, response, result)


@router.get("/me", response_model=AccountState)
def current(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return request.app.state.accounts.current(_session(request))


@router.patch("/me", response_model=AccountState)
def edit_profile(body: ProfileRequest, request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return request.app.state.accounts.profile(_session(request, True), body.display_name.strip())


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.app.state.accounts.logout(_session(request, True))
    return _clear(request)


@router.post("/revoke-sessions", response_model=AccountState)
def revoke_sessions(request: Request, response: Response):
    return _signed(request, response, request.app.state.accounts.revoke_all(_session(request, True)))


@router.post("/password", response_model=AccountState)
def update_password(body: PasswordChange, request: Request, response: Response):
    token = _session(request, True)
    _budget(request)
    result = request.app.state.accounts.update_password(token, body.current_password, body.new_password)
    return _signed(request, response, result)


@router.delete("/me", status_code=204)
def delete_account(body: DeleteAccount, request: Request):
    token = _session(request, True)
    _budget(request)
    request.app.state.accounts.delete(token, body.password)
    return _clear(request)
