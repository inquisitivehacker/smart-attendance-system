from sqlalchemy import Column, String, DateTime
from datetime import datetime
from src.database import Base

class SystemStatus(Base):
    __tablename__ = "system_status"
    
    component = Column(String, primary_key=True, index=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="ONLINE")
