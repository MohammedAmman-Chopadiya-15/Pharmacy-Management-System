from pydantic import BaseModel
from datetime import date
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class PatientPortalRegistration(BaseModel):
    NHS_Number: str
    FirstName: str
    LastName: str
    DateOfBirth: date
    Address: str
    Phone_Number: str
    Allergies: Optional[str] = "None"

class PatientPortalResponse(BaseModel):
    PrescriptionID: int
    MedicationName: str
    Dosage: str
    DatePrescribed: date
    Status: str
    DirectionsForUse: Optional[str] = None

    class Config:
        from_attributes = True

class VaccinationSummary(BaseModel):
    PatientName: str
    NHS_Number: str
    VaccineType: str
    TotalDoses: int
    LastDoseDate: date
    AdministeringDoctor: str

    class Config:
        from_attributes = True

class FacilityWorkload(BaseModel):
    FacilityName: str
    TotalPrescriptions: int
    PendingCount: int
    DispensedCount: int

    class Config:
        from_attributes = True