from app.core.database import Base

from .location import City, State
from .person import Person
from .plan import Plan
from .telegram_config import TelegramConfig
from .user import Permission, Role, User
from .client import Client
from .tenant import Tenant
from .channel import Channel
from .service import Service
from .conversation import Conversation
from .appointment import Appointment
from .message import Message
