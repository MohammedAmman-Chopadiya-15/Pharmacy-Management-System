from sqlalchemy import Column, Integer, String, Date, Text
from database import Base

class Patient(Base):
    __tablename__ = "PATIENTS"
    PatientID = Column(Integer, primary_key=True, index=True)
    NHS_Number = Column(String(10), unique=True)
    FirstName = Column(String(50))
    LastName = Column(String(50))
    DateOfBirth = Column(Date)
    Address = Column(String(255))
    Phone_Number = Column(String(15))
    Allergies = Column(Text)

class Medication(Base):
    __tablename__ = "MEDICATIONS"
    MedicationID = Column(Integer, primary_key=True, index=True)
    MedicationName = Column(String(100))
    Dosage = Column(String(50))
    Form_Type = Column(String(50))