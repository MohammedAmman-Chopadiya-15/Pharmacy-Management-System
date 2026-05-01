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

# POST AUTH: Login Endpoint
@app.post("/auth/login", response_model=schemas.Token, tags=["Security"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    POST AUTH: Authenticates a user and returns a JWT.
    Checks against the SYSTEM_USERS table in the database.
    """
    user = db.query(models.User).filter(models.User.Username == form_data.username).first()
    
    if not user or form_data.password != user.HashedPassword:
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


@app.post("/patients/register-portal", tags=["Patient Management"])
def register_patient_with_portal(
    data: schemas.PatientPortalRegistration, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Masters Level: Atomic Transaction.
    Creates a Patient and a System User account in a single operation.
    """
    # 1. Authorization: Only Staff/Admin can register new patients
    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Patients cannot register other patients")

    # 2. Create the Patient Record
    new_patient = models.Patient(
        NHS_Number=data.NHS_Number,
        FirstName=data.FirstName,
        LastName=data.LastName,
        DateOfBirth=data.DateOfBirth,
        Address=data.Address,
        Phone_Number=data.Phone_Number,
        Allergies=data.Allergies
    )
    db.add(new_patient)
    db.flush() # Flush to get the new_patient.PatientID before committing

    # 3. Generate Credentials and Create User Account
    # Logic: Username = FirstName, Password = NHSNumber + LastName
    suffix = data.NHS_Number[-3:]
    generated_username = f"{data.FirstName.lower()}{suffix}"
    generated_password = f"{data.NHS_Number}{data.LastName}"

    new_user = models.User(
        Username=generated_username,
        HashedPassword=generated_password,
        RoleID=5, # Role 5 is 'Patient'
        PatientID=new_patient.PatientID
    )
    db.add(new_user)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed. NHS Number or Username may already exist.")

    return {
        "message": "Patient and Portal account created successfully",
        "username": generated_username,
        "temporary_password": generated_password
    }

"""
Allows staff to issue multiple medications in one request.
Restricted to Staff/Admin (Roles 1-4).
"""

@app.post("/prescriptions/issue", tags=["Clinical Operations"])
def issue_bulk_prescriptions(
    bulk_data: schemas.BulkPrescription, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):

    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Patients cannot issue prescriptions")

    new_prescriptions = []
    
    for item in bulk_data.Items:
        # Lookup medicine ID by name
        med_record = db.query(models.Medication).filter(
            models.Medication.MedicationName.ilike(item.MedicationName)
        ).first()

        if not med_record:
            raise HTTPException(
                status_code=404, 
                detail=f"Medication '{item.MedicationName}' not found."
            )

        # Create entry with SPECIFIC directions for each medicine
        new_entry = models.Prescription(
            PatientID=bulk_data.PatientID,
            DoctorID=bulk_data.DoctorID,
            MedicationID=med_record.MedicationID,
            FacilityID=bulk_data.FacilityID,
            DatePrescribed=datetime.now().date(),
            Status="Pending",
            DirectionsForUse=item.Directions,
            Quantity=1
        )
        db.add(new_entry)
        new_prescriptions.append(new_entry)

    db.commit()
    return {"message": f"Successfully issued {len(new_prescriptions)} tailored prescriptions"}


"""
State Machine Transition.
Only allows Roles 1 (Admin) or 2 (Pharmacist) to update status to 'Dispensed'.
"""

@app.put("/prescriptions/{prescription_id}/dispense", tags=["Clinical Operations"])
def dispense_prescription(
    prescription_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Masters Level: Atomic State Transition with Inventory Reconciliation.
    """
    # 1. RBAC
    if current_user.RoleID not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only Pharmacists can dispense medication")

    # 2. Fetch the prescription record
    prescription = db.query(models.Prescription).filter(
        models.Prescription.PrescriptionID == prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # 3. Logic check: Prevent double-dispensing
    if prescription.Status in ["Dispensed", "Collected"]:
        raise HTTPException(status_code=400, detail="This prescription has already been dispensed/collected")

    # 4. Inventory Logic: Fetch the related Medication
    medication = db.query(models.Medication).filter(
        models.Medication.MedicationID == prescription.MedicationID
    ).first()

    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found in catalog")

    # 5. Check if we have enough stock
    if medication.StockQuantity < prescription.Quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock for {medication.MedicationName}. Available: {medication.StockQuantity}"
        )

    # 6. Perform updates in a single transaction
    try:
        # Update Prescription
        prescription.Status = "Dispensed"
        prescription.DateDispensed = datetime.now().date()
        prescription.DispensingPharmacist = current_user.Username

        # Deduct from Stock
        medication.StockQuantity -= prescription.Quantity
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal update failed. Transaction rolled back.")

    return {
        "message": f"Success: Prescription {prescription_id} marked as Dispensed",
        "stock_remaining": medication.StockQuantity
    }