from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.models.entities import Family, FamilyMember, RoleEnum
from app.schemas.families import (
    FamilyCreate,
    FamilyListResponse,
    FamilyMemberCreate,
    FamilyMemberListResponse,
    FamilyMemberResponse,
    FamilyMemberUpdate,
    FamilyResponse,
    FamilyUpdate,
)

router = APIRouter(prefix="/v1/families", tags=["families"])


@router.get("", response_model=FamilyListResponse)
def list_families(db: Session = Depends(get_db)):
    families = db.execute(select(Family).order_by(Family.id.asc())).scalars().all()
    return FamilyListResponse(items=[FamilyResponse.model_validate(item, from_attributes=True) for item in families])


@router.post("", response_model=FamilyResponse, status_code=201)
def create_family(payload: FamilyCreate, db: Session = Depends(get_db)):
    family = Family(name=payload.name)
    db.add(family)
    db.commit()
    db.refresh(family)
    return FamilyResponse.model_validate(family, from_attributes=True)


@router.get("/{family_id}", response_model=FamilyResponse)
def get_family(family_id: int, db: Session = Depends(get_db)):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")
    return FamilyResponse.model_validate(family, from_attributes=True)


@router.patch("/{family_id}", response_model=FamilyResponse)
def update_family(family_id: int, payload: FamilyUpdate, db: Session = Depends(get_db)):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")
    family.name = payload.name
    db.commit()
    db.refresh(family)
    return FamilyResponse.model_validate(family, from_attributes=True)


@router.delete("/{family_id}", status_code=204)
def delete_family(family_id: int, db: Session = Depends(get_db)):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")

    members_exist = db.execute(select(FamilyMember.id).where(FamilyMember.family_id == family_id).limit(1)).scalar_one_or_none()
    if members_exist is not None:
        raise HTTPException(status_code=409, detail="family has members; delete members first")

    db.delete(family)
    db.commit()


@router.get("/{family_id}/members", response_model=FamilyMemberListResponse)
def list_family_members(family_id: int, db: Session = Depends(get_db)):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")

    members = db.execute(
        select(FamilyMember).where(FamilyMember.family_id == family_id).order_by(FamilyMember.id.asc())
    ).scalars().all()
    return FamilyMemberListResponse(
        items=[
            FamilyMemberResponse(
                id=item.id,
                family_id=item.family_id,
                email=item.email,
                display_name=item.display_name,
                role=item.role.value,
            )
            for item in members
        ]
    )


@router.post("/{family_id}/members", response_model=FamilyMemberResponse, status_code=201)
def create_family_member(family_id: int, payload: FamilyMemberCreate, db: Session = Depends(get_db)):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="family not found")

    member = FamilyMember(
        family_id=family_id,
        email=payload.email,
        display_name=payload.display_name,
        role=RoleEnum(payload.role),
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already exists") from None

    db.refresh(member)
    return FamilyMemberResponse(
        id=member.id,
        family_id=member.family_id,
        email=member.email,
        display_name=member.display_name,
        role=member.role.value,
    )


@router.get("/{family_id}/members/{member_id}", response_model=FamilyMemberResponse)
def get_family_member(family_id: int, member_id: int, db: Session = Depends(get_db)):
    member = db.get(FamilyMember, member_id)
    if member is None or member.family_id != family_id:
        raise HTTPException(status_code=404, detail="family member not found")

    return FamilyMemberResponse(
        id=member.id,
        family_id=member.family_id,
        email=member.email,
        display_name=member.display_name,
        role=member.role.value,
    )


@router.patch("/{family_id}/members/{member_id}", response_model=FamilyMemberResponse)
def update_family_member(family_id: int, member_id: int, payload: FamilyMemberUpdate, db: Session = Depends(get_db)):
    member = db.get(FamilyMember, member_id)
    if member is None or member.family_id != family_id:
        raise HTTPException(status_code=404, detail="family member not found")

    if payload.display_name is not None:
        member.display_name = payload.display_name
    if payload.role is not None:
        member.role = RoleEnum(payload.role)

    db.commit()
    db.refresh(member)
    return FamilyMemberResponse(
        id=member.id,
        family_id=member.family_id,
        email=member.email,
        display_name=member.display_name,
        role=member.role.value,
    )


@router.delete("/{family_id}/members/{member_id}", status_code=204)
def delete_family_member(family_id: int, member_id: int, db: Session = Depends(get_db)):
    member = db.get(FamilyMember, member_id)
    if member is None or member.family_id != family_id:
        raise HTTPException(status_code=404, detail="family member not found")

    db.delete(member)
    db.commit()
