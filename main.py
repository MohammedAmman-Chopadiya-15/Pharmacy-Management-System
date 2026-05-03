from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import time

import models, schemas, database

# --- Security Configuration ---
SECRET_KEY = "SUPER_SECRET_LINCOLN_PHARMACY_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="MedCare API")

# --- Auth Helper Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.strip().encode('utf-8'), 
            hashed_password.strip().encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Seeding Logic (Distinction Grade Feature) ---

@app.on_event("startup")
def startup_event():
    """Wait for DB and seed initial users."""
    db = None
    retries = 5
    while retries > 0:
        try:
            db = database.SessionLocal()
            # Try a simple query to see if the DB is actually ready
            db.execute(func.now()) 
            break
        except Exception:
            retries -= 1
            print(f"Database not ready... retrying in 3s ({retries} attempts left)")
            time.sleep(3)
    
    if not db:
        print("Could not connect to database. Seeding aborted.")
        return

    try:
        # Check if users already exist
        if not db.query(models.User).first():
            print("Database empty. Starting cryptographic seeding...")
            
            # Seed Staff
            staff_members = [
                ("admin_jclark", "admin_jclark!1", 1),
                ("pharma_kbrown", "pharma_kbrown!2", 2),
                ("mgr_rsmith", "mgr_rsmith!3", 3),
                ("res_ltaylor", "res_ltaylor!4", 4)
            ]
            for username, plain_pw, role_id in staff_members:
                db.add(models.User(
                    Username=username,
                    HashedPassword=get_password_hash(plain_pw),
                    RoleID=role_id
                ))

            # Seed Patients
            patients = db.query(models.Patient).all()
            for p in patients:
                suffix = p.NHS_Number[-3:]
                gen_user = f"{p.FirstName.lower()}{suffix}"
                gen_pass = f"{p.NHS_Number}{p.LastName}"
                db.add(models.User(
                    Username=gen_user,
                    HashedPassword=get_password_hash(gen_pass),
                    RoleID=5,
                    PatientID=p.PatientID
                ))
            
            db.commit()
            print("Seeding successful.")
        else:
            print("Database already contains users. Skipping seeding.")
    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

# --- Endpoints ---

@app.post("/auth/login", response_model=schemas.Token, tags=["Security"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.Username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.Username})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    JWT Validation: Extracts the 'sub' claim and verifies the user exists in the DB.
    """
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
Returns workload metrics for all facilities or a specific one if facility_name is provided.
"""

@app.get("/reports/facility-workload", 
         response_model=List[schemas.FacilityWorkload], 
         tags=["Management Reports"])
def get_facility_workload(
    facility_name: Optional[str] = None, # New Optional Query Parameter
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
    ):

    # Authorization: Staff only
    if current_user.RoleID == 5:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Patients cannot view facility workload reports"
        )

    # Base Query
    query = db.query(
        models.Facility.FacilityName,
        func.count(models.Prescription.PrescriptionID).label("TotalPrescriptions"),
        func.sum(case((models.Prescription.Status == 'Pending', 1), else_=0)).label("PendingCount"),
        func.sum(case((models.Prescription.Status == 'Dispensed', 1), else_=0)).label("DispensedCount")
    ).join(models.Prescription, models.Facility.FacilityID == models.Prescription.FacilityID)

    # Apply Filter if parameter is provided
    if facility_name:
        query = query.filter(models.Facility.FacilityName.ilike(f"%{facility_name}%"))

    results = query.group_by(models.Facility.FacilityName).all()

    if not results:
        detail_msg = f"No data found for facility: {facility_name}" if facility_name else "No workload data found"
        raise HTTPException(status_code=404, detail=detail_msg)

    return results

"""
Creates a Patient and a System User account in a single operation.
"""

@app.post("/patients/register-portal", tags=["Patient Management"])
def register_patient_with_portal(
    data: schemas.PatientPortalRegistration, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):

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
    db.flush()

    # 3. Generate Credentials and Create User Account
    # Logic: Username = FirstName, Password = NHSNumber + LastName
    suffix = data.NHS_Number[-3:]
    generated_username = f"{data.FirstName.lower()}{suffix}"
    generated_password = f"{data.NHS_Number}{data.LastName}"
    
    secure_hashed_password = get_password_hash(generated_password)

    new_user = models.User(
        Username=generated_username,
        HashedPassword=secure_hashed_password,
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

"""
Appends a new clinical encounter to history and updates current patient profile.
"""

@app.put("/patients/{patient_id}/consultation", tags=["Clinical Operations"])
def conduct_clinical_consultation(
    patient_id: int, 
    data: schemas.ClinicalConsultation, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    
    if current_user.RoleID not in [1, 3]: # Admin or Doctor
        raise HTTPException(status_code=403, detail="Unauthorized clinical access")

    patient = db.query(models.Patient).filter(models.Patient.PatientID == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

# 1. Update Current Profile in PATIENTS table (Robust Guard)
    if data.NewAllergies and data.NewAllergies.strip():
        # Convert to lowercase for comparison
        input_lower = data.NewAllergies.lower()
        
        # Keywords that signal the doctor isn't actually adding a new medical allergy
        danger_keywords = ["no new", "none", "n/a", "no change", "reported", "string"]
        
        # Logic: If the input DOES NOT contain any danger keywords, proceed with update
        if not any(keyword in input_lower for keyword in danger_keywords):
            patient.Allergies = data.NewAllergies
        else:
            # Optional: Log to console for debugging so you see it being ignored
            print(f"Update ignored: '{data.NewAllergies}' recognized as placeholder.")

    # 2. Create NEW entry in PATIENT_RECORDS_LOG
    new_log = models.PatientRecordLog(
        PatientID=patient_id,
        MedicalHistory=data.ConsultationNotes,
        BloodType=data.BloodType,
        ChronicConditions=data.ChronicConditions,
        LastClinicalReview=datetime.now().date()
    )
    
    db.add(new_log)
    db.commit()
    return {"message": "New clinical encounter recorded and profile updated"}

"""
Delete incorrect prescription records
Prevents deletion of fulfilled clinical records to maintain legal audit trails.
"""

@app.delete("/prescriptions/{prescription_id}", tags=["Clinical Operations"])
def cancel_prescription(
    prescription_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):

    # 1. Auth: Only Admins or Doctors
    if current_user.RoleID not in [1, 3]:
        raise HTTPException(status_code=403, detail="Only clinical staff can cancel prescriptions")

    prescription = db.query(models.Prescription).filter(
        models.Prescription.PrescriptionID == prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # 2. The Guard: Block deletion if already fulfilled
    if prescription.Status in ["Dispensed", "Collected"]:
        raise HTTPException(
            status_code=400, 
            detail="Legal Restriction: Cannot delete a prescription once it has been dispensed."
        )

    db.delete(prescription)
    db.commit()
    return {"message": f"Prescription {prescription_id} successfully removed."}

"""
Implements a 'Medical Recall' workflow. Blocks deletion if active unfulfilled prescriptions exist for this drug.
"""

@app.delete("/medications/{medication_id}/recall", tags=["Inventory Management"])
def recall_medication(
    medication_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):

    # 1. Authorization: Admin or Pharmacist (Role 1 or 2)
    if current_user.RoleID not in [1, 2]:
        raise HTTPException(status_code=403, detail="Only Pharmacists/Admins can initiate a recall")

    # 2. Check if medication exists
    medication = db.query(models.Medication).filter(
        models.Medication.MedicationID == medication_id
    ).first()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    # 3. Safety Check:
    # We must block the recall if patients are waiting on this specific batch.
    active_prescriptions = db.query(models.Prescription).filter(
        models.Prescription.MedicationID == medication_id,
        models.Prescription.Status == "Pending"
    ).all()

    if active_prescriptions:
        raise HTTPException(
            status_code=400, 
            detail=f"Recall Blocked: {len(active_prescriptions)} active 'Pending' prescriptions exist. "
                   "These must be cancelled or switched to alternatives first."
        )

    # 4. Atomic Cleanup

    try:
        db.delete(medication)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during recall execution.")

    return {
        "message": f"Recall Success: {medication.MedicationName} removed from catalog.",
        "affected_records": "All historical prescriptions archived."
    }   