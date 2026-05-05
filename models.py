from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, func
from sqlalchemy.orm import relationship
from database import Base

# Simple lookup table for user permissions based on ROLE in USER_ROLES
class UserRole(Base):
    __tablename__ = "USER_ROLES"
    RoleID = Column(Integer, primary_key=True, index=True)
    RoleName = Column(String(50), unique=True)

# MAIN SYSTEM_USERS table with user accounts
class User(Base):
    __tablename__ = "SYSTEM_USERS"
    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, index=True)
    HashedPassword = Column(String(255))
    RoleID = Column(Integer, ForeignKey("USER_ROLES.RoleID"))
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"), nullable=True) # Is kept nullable as staff don't have patient ID
    
    role = relationship("UserRole")

# Used to track the issued medicine prescriptions
class Prescription(Base):
    __tablename__ = "PRESCRIPTIONS"
    PrescriptionID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"))
    DoctorID = Column(Integer, ForeignKey("DOCTORS.DoctorID"))
    MedicationID = Column(Integer, ForeignKey("MEDICATIONS.MedicationID"))
    FacilityID = Column(Integer, ForeignKey("FACILITIES.FacilityID"))
    DatePrescribed = Column(Date, nullable=False)
    DateDispensed = Column(Date, nullable=True)
    Quantity = Column(Integer, default=1) 
    DirectionsForUse = Column(Text)
    DispensingPharmacist = Column(String(100))
    Status = Column(String(20), default="Pending")


class Facility(Base):
    __tablename__ = "FACILITIES"
    FacilityID = Column(Integer, primary_key=True, index=True)
    FacilityName = Column(String(100))
    Full_Address = Column(String(255))


# Created Database VIEW to make sure patient can only access his/her own data
class PatientSelfService(Base):
    __tablename__ = "Patient_Self_Service_View"
    PrescriptionID = Column(Integer, primary_key=True)
    PatientID = Column(Integer) 
    MedicationName = Column(String(100))
    Dosage = Column(String(50))
    DatePrescribed = Column(Date)
    Status = Column(String(20))
    DirectionsForUse = Column(Text)

# Model to match DOCTORS table in db
class Doctor(Base):
    __tablename__ = "DOCTORS"
    DoctorID = Column(Integer, primary_key=True, index=True)
    PrescriberName = Column(String(100))
    FacilityID = Column(Integer, ForeignKey("FACILITIES.FacilityID"))

# Refers to VACCINATIONS table in db
class Vaccination(Base):
    __tablename__ = "VACCINATIONS"
    VaccinationID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"))
    DoctorID = Column(Integer, ForeignKey("DOCTORS.DoctorID"))
    VaccineType = Column(String(100))
    DoseNumber = Column(Integer)
    DateAdministered = Column(Date)

# Patient table with basic information
class Patient(Base):
    __tablename__ = "PATIENTS"
    PatientID = Column(Integer, primary_key=True, index=True)
    NHS_Number = Column(String(10), unique=True)
    FirstName = Column(String(50))
    LastName = Column(String(50))
    DateOfBirth = Column(Date)
    Address = Column(String(255))
    Allergies = Column(String(255), default="None")
    Phone_Number = Column(String(15))

# List of all available drugs and stock (MEDICATIONS in db)
class Medication(Base):
    __tablename__ = "MEDICATIONS"
    MedicationID = Column(Integer, primary_key=True, index=True)
    MedicationName = Column(String(100), nullable=False)
    Dosage = Column(String(50))
    StockQuantity = Column(Integer, default=0)

# Clinical log to keep track of patient history without overwriting previous visits
class PatientRecordLog(Base):
    __tablename__ = "PATIENT_RECORDS_LOG"
    LogID = Column(Integer, primary_key=True, index=True) 
    PatientID = Column(Integer, ForeignKey("PATIENTS.PatientID"))
    MedicalHistory = Column(Text)
    BloodType = Column(String(3))
    ChronicConditions = Column(Text)
    LastClinicalReview = Column(Date)