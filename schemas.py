from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

class PatientBase(BaseModel):
    NHS_Number: str = Field(..., min_length=10, max_length=10)
    FirstName: str
    LastName: str
    DateOfBirth: date
    Address: Optional[str] = None
    Phone_Number: Optional[str] = None
    Allergies: Optional[str] = None

class PatientResponse(PatientBase):
    PatientID: int
    class Config:
        from_attributes = True

class MedicationBase(BaseModel):
    MedicationName: str
    Dosage: str
    Form_Type: str

class MedicationResponse(MedicationBase):
    MedicationID: int
    class Config:
        from_attributes = True