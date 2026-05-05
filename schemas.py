from pydantic import BaseModel
from datetime import date
from typing import Optional, List

# --- Security & Session Schemas ---

class Token(BaseModel):
    # This defines the structure of the JWT returned to the user after login
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # Used for internal decoding of the JWT payload
    username: Optional[str] = None

class UserLogin(BaseModel):
    # Format for recieving credentials from the login endpoint
    username: str
    password: str


# --- Patient Management Schemas ---

class PatientPortalRegistration(BaseModel):
    # Required fields for onboarding a new patient into the system
    NHS_Number: str
    FirstName: str
    LastName: str
    DateOfBirth: date
    Address: str
    Phone_Number: str
    Allergies: Optional[str] = "None"

class PatientPortalResponse(BaseModel):
    # Defining exactl patient information schema for the 'My Prescriptions' endpoint view
    PrescriptionID: int
    MedicationName: str
    Dosage: str
    DatePrescribed: date
    Status: str
    DirectionsForUse: Optional[str] = None

    class Config:
        # from_attributes allows Pydantic to read data from SQLAlchemy objects
        from_attributes = True


# --- Management & Reporting Schemas ---

class VaccinationSummary(BaseModel):
    # Structure for the aggregated public health reports
    PatientName: str
    NHS_Number: str
    VaccineType: str
    TotalDoses: int
    LastDoseDate: date
    AdministeringDoctor: str

    class Config:
        from_attributes = True

class FacilityWorkload(BaseModel):
    # For the management dashboard to track location-specific bottlenecks
    FacilityName: str
    TotalPrescriptions: int
    PendingCount: int
    DispensedCount: int

    class Config:
        from_attributes = True


# --- Clinical Operations Schemas ---

class MedicationEntry(BaseModel):
    # Model used specifically for the bulk prescription list
    MedicationName: str
    Directions: str

class BulkPrescription(BaseModel):
    # Handles insertion of multiple records (prescriptions) at same time
    PatientID: int
    DoctorID: int
    FacilityID: int
    Items: List[MedicationEntry]

    class Config:
        from_attributes = True

class ClinicalConsultation(BaseModel):
    # Captures notes and updates patient vitals during a check-up
    ConsultationNotes: str
    NewAllergies: Optional[str] = None
    BloodType: Optional[str] = None
    ChronicConditions: Optional[str] = None

    class Config:
        from_attributes = True