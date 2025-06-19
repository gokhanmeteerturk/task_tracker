from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from application.usecases import (
    ListPlatformsUseCase,
    CreatePlatformUseCase,
    GetPlatformUseCase,
    CreateAccountUseCase,
    ListAccountsByPlatformUseCase,
    DeleteAccountUseCase,
)
from ..dependencies import get_db, get_platform_repo, get_account_repo

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/platforms", response_class=HTMLResponse)
def get_platforms_page(req: Request, db: Session = Depends(get_db)):
    use_case = ListPlatformsUseCase(get_platform_repo(db))
    platforms = use_case.execute()
    return templates.TemplateResponse(
        "platforms.html",
        {"request": req, "platforms": platforms, "page_title": "Manage Platforms"},
    )


@router.post("/platforms/add")
def add_platform(
    name: str = Form(...), config: str = Form("{}"), db: Session = Depends(get_db)
):
    try:
        config_dict = json.loads(config)
    except Exception:
        config_dict = {}
    use_case = CreatePlatformUseCase(get_platform_repo(db))
    use_case.execute(name=name, config=config_dict)
    return RedirectResponse(url="/platforms", status_code=303)


@router.get("/platforms/{platform_id}/accounts", response_class=HTMLResponse)
def get_accounts_page(req: Request, platform_id: int, db: Session = Depends(get_db)):
    plat_repo = get_platform_repo(db)
    acc_repo = get_account_repo(db)

    platform = GetPlatformUseCase(plat_repo).execute(platform_id)
    accounts = ListAccountsByPlatformUseCase(acc_repo).execute(platform_id)

    return templates.TemplateResponse(
        "accounts.html",
        {
            "request": req,
            "platform": platform,
            "accounts": accounts,
            "page_title": f"Accounts for {platform.name}",
        },
    )


@router.post("/platforms/{platform_id}/accounts/add")
def add_account(
    platform_id: int,
    username: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db),
):
    use_case = CreateAccountUseCase(get_account_repo(db))
    use_case.execute(platform_id=platform_id, username=username, notes=notes)
    return RedirectResponse(url=f"/platforms/{platform_id}/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
def delete_account(
    account_id: int, platform_id: int = Form(...), db: Session = Depends(get_db)
):
    use_case = DeleteAccountUseCase(get_account_repo(db))
    use_case.execute(account_id=account_id)
    return RedirectResponse(url=f"/platforms/{platform_id}/accounts", status_code=303)


from application.usecases import UpdatePlatformUseCase
import json


@router.get("/platforms/{platform_id}/edit", response_class=HTMLResponse)
def edit_platform_page(req: Request, platform_id: int, db: Session = Depends(get_db)):
    plat_repo = get_platform_repo(db)
    platform = GetPlatformUseCase(plat_repo).execute(platform_id)
    return templates.TemplateResponse(
        "edit_platform.html",
        {
            "request": req,
            "platform": platform,
            "page_title": f"Edit Platform: {platform.name}",
        },
    )


@router.post("/platforms/{platform_id}/edit")
def edit_platform(
    platform_id: int,
    name: str = Form(...),
    config: str = Form("{}"),
    db: Session = Depends(get_db),
):
    plat_repo = get_platform_repo(db)
    try:
        config_dict = json.loads(config)
    except Exception:
        config_dict = {}
    UpdatePlatformUseCase(plat_repo).execute(platform_id, name, config_dict)
    return RedirectResponse(url="/platforms", status_code=303)
