from sqlalchemy import Column, Integer, String, Date, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    hire_date = Column(Date, nullable=False)
    work_schedule = Column(JSON, nullable=True)

    # Relationship
    user = relationship("User", back_populates="employee", uselist=False)