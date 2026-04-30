from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

import models, schemas, database

# --- Security Configuration ---
SECRET_KEY = "SUPER_SECRET_LINCOLN_PHARMACY_KEY"  # In a real app, use an Env Var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup password hashing and OAuth2 scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="MedCare API")

# --- Auth Helper Functions ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "MedCare API is live and running in Docker!"}

# POST AUTH: Login Endpoint
@app.post("/auth/login", response_model=schemas.Token, tags=["Security"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    POST AUTH: Authenticates a user and returns a JWT.
    Checks against the SYSTEM_USERS table in the database.
    """
    user = db.query(models.User).filter(models.User.Username == form_data.username).first()
    
    # For the Masters demo, we check against the plain text 'password123' 
    # to match the initial DML state. 
    if not user or form_data.password != "password123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.Username})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.Username == username).first()
    if user is None:
        raise credentials_exception
    return user

# SECURE ENDPOINT: No ID in the URL
@app.get("/my-prescriptions/me", 
         response_model=List[schemas.PatientPortalResponse], 
         tags=["Patient Portal"])
def get_my_own_prescriptions(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(database.get_db)
):
    """
    Masters Level: This endpoint is now truly secure. It ignores URL inputs 
    and uses the PatientID linked to the authenticated JWT session.
    """
    # Verify this user is actually a patient
    if current_user.PatientID is None:
        raise HTTPException(status_code=403, detail="This account is not linked to a patient record")

    # Use the PatientID from the DATABASE
    results = db.query(models.PatientSelfService).filter(
        models.PatientSelfService.PatientID == current_user.PatientID
    ).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No prescriptions found for your account")
        
    return results




@app.get("/reports/vaccination-coverage/{vaccine_type}", 
         response_model=List[schemas.VaccinationSummary], 
         tags=["Management Reports"])
def get_vaccination_report(
    vaccine_type: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
    ):
    """Joins PATIENTS, VACCINATIONS, and DOCTORS to track clinical progress."""
    # Block patients (Role 5) from seeing aggregate reports
    if current_user.RoleID == 5:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Patients cannot view management reports"
        )
    
    results = db.query(
        func.concat(models.Patient.FirstName, ' ', models.Patient.LastName).label("PatientName"),
        models.Patient.NHS_Number,
        models.Vaccination.VaccineType,
        func.count(models.Vaccination.VaccinationID).label("TotalDoses"),
        func.max(models.Vaccination.DateAdministered).label("LastDoseDate"),
        models.Doctor.PrescriberName.label("AdministeringDoctor")
    ).join(models.Vaccination, models.Patient.PatientID == models.Vaccination.PatientID)\
     .join(models.Doctor, models.Vaccination.DoctorID == models.Doctor.DoctorID)\
     .filter(models.Vaccination.VaccineType.ilike(f"%{vaccine_type}%"))\
     .group_by(models.Patient.PatientID, models.Vaccination.VaccineType, models.Doctor.PrescriberName)\
     .all()

    if not results:
        raise HTTPException(status_code=404, detail=f"No records found for vaccine: {vaccine_type}")

    return results

"""
Management Analytics.
Uses conditional aggregation to provide facility performance metrics.
Restricted to Staff/Admin roles.
"""

@app.get("/reports/facility-workload", 
         response_model=List[schemas.FacilityWorkload], 
         tags=["Management Reports"])
def get_facility_workload(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Authorization: Only Staff (Roles 1-4) should see management reports
    if current_user.RoleID == 5:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Patients cannot view facility workload reports"
        )

    # Query logic: Join Facilities to Prescriptions and count statuses
    results = db.query(
        models.Facility.FacilityName,
        func.count(models.Prescription.PrescriptionID).label("TotalPrescriptions"),
        func.sum(func.if_(models.Prescription.Status == 'Pending', 1, 0)).label("PendingCount"),
        func.sum(func.if_(models.Prescription.Status == 'Dispensed', 1, 0)).label("DispensedCount")
    ).join(models.Prescription, models.Facility.FacilityID == models.Prescription.FacilityID)\
     .group_by(models.Facility.FacilityName)\
     .all()

    if not results:
        raise HTTPException(status_code=404, detail="No facility workload data found")

    return results