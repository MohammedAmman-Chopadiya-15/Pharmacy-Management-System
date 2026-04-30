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

