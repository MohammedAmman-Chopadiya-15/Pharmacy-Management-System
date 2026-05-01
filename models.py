from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, func
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


class Prescription(Base):
    __tablename__ = "PRESCRIPTIONS"

    PrescriptionID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"))
    DoctorID = Column(Integer, ForeignKey("DOCTORS.DoctorID"))
    MedicationID = Column(Integer, ForeignKey("MEDICATIONS.MedicationID"))
    FacilityID = Column(Integer, ForeignKey("FACILITIES.FacilityID"))
    DatePrescribed = Column(Date, nullable=False)
    DateDispensed = Column(Date, nullable=True)
    Quantity = Column(Integer, default=1) # Added to match NOT NULL constraint
    DirectionsForUse = Column(Text)
    NumberOfRepeats = Column(Integer, default=0)
    DispensingPharmacist = Column(String(100))
    Status = Column(String(20), default="Pending")


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


class Doctor(Base):
    __tablename__ = "DOCTORS"
    DoctorID = Column(Integer, primary_key=True, index=True)
    PrescriberName = Column(String(100))
    FacilityID = Column(Integer, ForeignKey("FACILITIES.FacilityID"))

class Vaccination(Base):
    __tablename__ = "VACCINATIONS"
    VaccinationID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"))
    DoctorID = Column(Integer, ForeignKey("DOCTORS.DoctorID"))
    VaccineType = Column(String(100))
    DoseNumber = Column(Integer)
    DateAdministered = Column(Date)

class Facility(Base):
    __tablename__ = "FACILITIES"
    FacilityID = Column(Integer, primary_key=True, index=True)
    FacilityName = Column(String(100))
    Full_Address = Column(String(255))

class Patient(Base):
    __tablename__ = "PATIENTS"
    PatientID = Column(Integer, primary_key=True, index=True)
    NHS_Number = Column(String(10), unique=True)
    FirstName = Column(String(50))
    LastName = Column(String(50))
    DateOfBirth = Column(Date)
    Address = Column(String(255))
    Phone_Number = Column(String(15))
    Allergies = Column(String(255), default="None")

    # Relationships
    vaccinations = relationship("Vaccination", backref="patient")

class Medication(Base):
    __tablename__ = "MEDICATIONS"

    MedicationID = Column(Integer, primary_key=True, index=True)
    MedicationName = Column(String(100), nullable=False)
    Dosage = Column(String(50))
    Form_Type = Column(String(50))
    StockQuantity = Column(Integer, default=0)