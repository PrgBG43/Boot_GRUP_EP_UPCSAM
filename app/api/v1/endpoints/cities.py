from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.location import City
from app.schemas.city import CityCreate, CityResponse, CityUpdate
from app.repositories import city_repository

router = APIRouter()


@router.post("/", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
def create_city(city: CityCreate, db: Session = Depends(get_db)):
    return city_repository.create_city(db, city)


@router.get("/", response_model=List[CityResponse])
def list_cities(
    skip: int = 0,
    limit: int = 500,
    state_id: Optional[int] = Query(None, description="Filtrar ciudades por departamento"),
    db: Session = Depends(get_db),
):
    query = db.query(City)
    if state_id is not None:
        query = query.filter(City.state_id == state_id)
    return query.order_by(City.name).offset(skip).limit(limit).all()


@router.get("/{city_id}", response_model=CityResponse)
def get_city(city_id: int, db: Session = Depends(get_db)):
    city = city_repository.get_city(db, city_id)
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
    return city


@router.put("/{city_id}", response_model=CityResponse)
def update_city(city_id: int, city: CityUpdate, db: Session = Depends(get_db)):
    updated = city_repository.update_city(db, city_id, city)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
    return updated


@router.delete("/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_city(city_id: int, db: Session = Depends(get_db)):
    deleted = city_repository.delete_city(db, city_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
