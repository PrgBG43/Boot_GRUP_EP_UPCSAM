from sqlalchemy.orm import Session

from app.models.location import City
from app.schemas.city import CityCreate, CityUpdate


def list_cities(db: Session, skip: int = 0, limit: int = 100):
    return db.query(City).offset(skip).limit(limit).all()


def create_city(db: Session, city_in: CityCreate):
    city = City(**city_in.model_dump())
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


def get_city(db: Session, city_id: int):
    return db.query(City).filter(City.id == city_id).first()


def update_city(db: Session, city_id: int, city_in: CityUpdate):
    city = get_city(db, city_id)
    if not city:
        return None
    data = city_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(city, key, value)
    db.commit()
    db.refresh(city)
    return city


def delete_city(db: Session, city_id: int):
    city = get_city(db, city_id)
    if not city:
        return None
    db.delete(city)
    db.commit()
    return city
