from sqlalchemy.orm import Session

from app.models.location import State
from app.schemas.state import StateCreate, StateUpdate


def list_states(db: Session, skip: int = 0, limit: int = 100):
    return db.query(State).offset(skip).limit(limit).all()


def create_state(db: Session, state_in: StateCreate):
    state = State(**state_in.model_dump())
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def get_state(db: Session, state_id: int):
    return db.query(State).filter(State.id == state_id).first()


def update_state(db: Session, state_id: int, state_in: StateUpdate):
    state = get_state(db, state_id)
    if not state:
        return None
    data = state_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(state, key, value)
    db.commit()
    db.refresh(state)
    return state


def delete_state(db: Session, state_id: int):
    state = get_state(db, state_id)
    if not state:
        return None
    db.delete(state)
    db.commit()
    return state
