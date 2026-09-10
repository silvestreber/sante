from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db.database import get_db
from app.db.models import EntryType, FinanceEntry, User, UserRole

router = APIRouter(prefix="/api/finance", tags=["finance"])

admin_only = require_role(UserRole.ADMIN)


class FinanceEntryCreate(BaseModel):
    entry_type: EntryType
    amount: float
    description: str
    category: str | None = None
    date: str


class FinanceEntryUpdate(BaseModel):
    entry_type: EntryType | None = None
    amount: float | None = None
    description: str | None = None
    category: str | None = None
    date: str | None = None


@router.get("/entries")
def list_entries(
    start: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    entry_type: EntryType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    q = db.query(FinanceEntry).filter(
        FinanceEntry.date >= date.fromisoformat(start),
        FinanceEntry.date <= date.fromisoformat(end),
    )
    if entry_type:
        q = q.filter(FinanceEntry.entry_type == entry_type)
    entries = q.order_by(FinanceEntry.date.desc()).all()
    return [
        {
            "id": e.id,
            "entry_type": e.entry_type.value,
            "amount": e.amount,
            "description": e.description,
            "category": e.category,
            "date": e.date.isoformat(),
        }
        for e in entries
    ]


@router.get("/balance")
def get_balance(
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    base = db.query(func.coalesce(func.sum(FinanceEntry.amount), 0)).filter(
        FinanceEntry.date >= start_date, FinanceEntry.date <= end_date
    )
    income = base.filter(FinanceEntry.entry_type == EntryType.INCOME).scalar()
    expense = base.filter(FinanceEntry.entry_type == EntryType.EXPENSE).scalar()
    return {"income": income, "expense": expense, "balance": income - expense}


@router.post("/entries", status_code=201)
def create_entry(
    data: FinanceEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    entry = FinanceEntry(
        entry_type=data.entry_type,
        amount=data.amount,
        description=data.description.strip(),
        category=data.category.strip() if data.category else None,
        date=date.fromisoformat(data.date),
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "message": "Entrada registrada"}


@router.put("/entries/{entry_id}")
def update_entry(
    entry_id: int,
    data: FinanceEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    entry = db.query(FinanceEntry).filter(FinanceEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    if data.entry_type is not None:
        entry.entry_type = data.entry_type
    if data.amount is not None:
        entry.amount = data.amount
    if data.description is not None:
        entry.description = data.description.strip()
    if data.category is not None:
        entry.category = data.category.strip() or None
    if data.date is not None:
        entry.date = date.fromisoformat(data.date)
    db.commit()
    return {"message": "Entrada actualizada"}


@router.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    entry = db.query(FinanceEntry).filter(FinanceEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    db.delete(entry)
    db.commit()
    return {"message": "Entrada eliminada"}
