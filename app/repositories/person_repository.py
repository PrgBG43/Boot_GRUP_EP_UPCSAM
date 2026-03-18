from sqlalchemy.orm import Session

from app.models.person import Person
from app.schemas.person import PersonCreate, PersonUpdate


def list_persons(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Person).offset(skip).limit(limit).all()


def create_person(db: Session, person_in: PersonCreate):
    person = Person(**person_in.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def get_person(db: Session, person_id: int):
    return db.query(Person).filter(Person.id == person_id).first()


def update_person(db: Session, person_id: int, person_in: PersonUpdate):
    person = get_person(db, person_id)
    if not person:
        return None
    data = person_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(person, key, value)
    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, person_id: int):
    person = get_person(db, person_id)
    if not person:
        return None
    db.delete(person)
    db.commit()
    return person
