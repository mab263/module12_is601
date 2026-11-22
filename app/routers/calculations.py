"""Calculation endpoints: Browse, Read, Edit, Add, and Delete."""

import math
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculation_factory import CalculationFactory
from app.database import get_db
from app.models import Calculation
from app.schemas import CalculationCreate, CalculationRead

router = APIRouter(prefix="/calculations", tags=["calculations"])

# Ids are 32-bit integers in the database, so anything outside this range cannot exist.
CalculationId = Annotated[int, Path(ge=1, le=2_147_483_647)]


def get_calculation_or_404(db: Session, calculation_id: int) -> Calculation:
    """Return the calculation, or raise a 404 if there is no such record."""
    calculation = db.get(Calculation, calculation_id)
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found"
        )
    return calculation


def compute_result(data: CalculationCreate) -> float:
    """Run the calculation with the factory, refusing results too large to store or return."""
    result = CalculationFactory.calculate(data.type, data.a, data.b)
    if not math.isfinite(result):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Result is out of range",
        )
    return result


@router.get("", response_model=List[CalculationRead])
def browse_calculations(
    skip: int = Query(0, ge=0, le=2_147_483_647),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List calculations in id order, one page at a time."""
    statement = select(Calculation).order_by(Calculation.id).offset(skip).limit(limit)
    return db.scalars(statement).all()


@router.post("", response_model=CalculationRead, status_code=status.HTTP_201_CREATED)
def add_calculation(data: CalculationCreate, db: Session = Depends(get_db)):
    """Create a calculation. The server computes and stores the result."""
    calculation = Calculation(
        a=data.a,
        b=data.b,
        type=data.type.value,
        result=compute_result(data),
    )
    db.add(calculation)
    db.commit()
    db.refresh(calculation)
    return calculation


@router.get("/{calculation_id}", response_model=CalculationRead)
def read_calculation(calculation_id: CalculationId, db: Session = Depends(get_db)):
    """Return one calculation."""
    return get_calculation_or_404(db, calculation_id)


@router.put("/{calculation_id}", response_model=CalculationRead)
def edit_calculation(
    calculation_id: CalculationId,
    data: CalculationCreate,
    db: Session = Depends(get_db),
):
    """Replace a calculation's inputs and type. The result is recomputed."""
    calculation = get_calculation_or_404(db, calculation_id)
    result = compute_result(data)  # compute first, so a failure changes nothing
    calculation.a = data.a
    calculation.b = data.b
    calculation.type = data.type.value
    calculation.result = result
    db.commit()
    db.refresh(calculation)
    return calculation


@router.delete("/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(calculation_id: CalculationId, db: Session = Depends(get_db)):
    """Delete a calculation."""
    calculation = get_calculation_or_404(db, calculation_id)
    db.delete(calculation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)