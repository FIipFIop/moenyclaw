import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.token import DashboardToken

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

TOKEN_TTL_HOURS = 1


@router.post("")
async def create_token(db: AsyncSession = Depends(get_db)):
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    record = DashboardToken(token=token, expires_at=expires_at)
    db.add(record)
    await db.commit()
    return {"token": token, "expires_at": expires_at}


@router.get("/{token}/validate")
async def validate_token(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DashboardToken).where(DashboardToken.token == token))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=401, detail="Token not found")
    if record.used:
        raise HTTPException(status_code=401, detail="Token already used")
    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")

    record.used = True
    await db.commit()
    return {"valid": True, "expires_at": record.expires_at}
