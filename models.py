from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class UserRole(Base):
    __tablename__ = "USER_ROLES"
    RoleID = Column(Integer, primary_key=True, index=True)
    RoleName = Column(String(50), unique=True)

class User(Base):
    __tablename__ = "SYSTEM_USERS"
    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, index=True)
    HashedPassword = Column(String(255))
    RoleID = Column(Integer, ForeignKey("USER_ROLES.RoleID"))
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"), nullable=True)
    
    role = relationship("UserRole")

# Original table required for the .filter() logic in main.py
class Prescription(Base):
    __tablename__ = "PRESCRIPTIONS"
    PrescriptionID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer)


# The Security View
class PatientSelfService(Base):
    __tablename__ = "Patient_Self_Service_View"
    PrescriptionID = Column(Integer, primary_key=True)
    PatientID = Column(Integer)  # This MUST be here for the .filter() in main.py to work
    MedicationName = Column(String(100))
    Dosage = Column(String(50))
    DatePrescribed = Column(Date)
    Status = Column(String(20))
    DirectionsForUse = Column(Text)