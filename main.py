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

# --- Security & Auth Settings ---
SECRET_KEY = "SUPER_SECRET_LINCOLN_PHARMACY_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="MedCare API")

# --- Security Logic ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Basic check to see if the input password matches stored hash in database.
    try:
        return bcrypt.checkpw(
            plain_password.strip().encode('utf-8'), 
            hashed_password.strip().encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    # Standard bcrypt hashing using 'rounds=12' to balance speed and security
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict):
    # Used to generate the JWT for every session and sets a 30-minute expiry time
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- System Startup & Data Seeding ---

@app.on_event("startup")
def startup_event():
    # Function has been made to fix connection race condition:
    # Keeps the loop running to connect until the DB is actually ready so that app doesn't crash.
    db = None
    retries = 10
    while retries > 0:
        try:
            db = database.SessionLocal()
            db.execute(func.now()) 
            break
        except Exception:
            retries -= 1
            print(f"Waiting for database... {retries} retries left")
            time.sleep(5)
    
    if not db:
        return

    try:
        # COndition to check if base users exist
        if not db.query(models.User).first():
            print("Running initial cryptographic seeding for staff and patients...")
            
            # Creating default staff accounts (Admin, Pharmacist, Manager, Researcher)
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

            # Loop to create portal accounts and add to SYSTEM_USERS for every existing patient using a pattern as password
            patients = db.query(models.Patient).all()
            for p in patients:
                suffix = p.NHS_Number[-3:]
                gen_user = f"{p.FirstName.lower()}{suffix}"
                gen_pass = f"{p.NHS_Number}{p.LastName}"
                db.add(models.User(
                    Username=gen_user,
                    HashedPassword=get_password_hash(gen_pass),
                    RoleID=5, # Patient role is 5 in USER_ROLES
                    PatientID=p.PatientID
                ))
            
            db.commit()
        else:
            print("System already seeded. Ready.")
    except Exception as e:
        db.rollback()
    finally:
        db.close()

# ---------------------------------------
# --- Authentication Endpoints (POST) ---
# ---------------------------------------


# Authenticates users by verifying credentials against the database and returning a secure JWT for session management.
@app.post("/auth/login", response_model=schemas.Token, tags=["Security"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    # This is a standard login gate: finds user, checks the hash againts db, and returns the token
    user = db.query(models.User).filter(models.User.Username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login details",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.Username})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    # Custom function decodes the JWT to make sure the user is who they say they are for every request
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid",
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

# ----------------------------------
# --- Patient Portal Endpoints -----
# ----------------------------------


# Securely retrieves the personal prescription history for the currently logged-in patient using their unique session ID.
@app.get("/my-prescriptions/me", 
         response_model=List[schemas.PatientPortalResponse], 
         tags=["Patient Portal"])
def get_my_own_prescriptions(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(database.get_db)
):
    # This is built to be "tamper-proof", only shows data based on the logged-in user's ID
    # Uses token to verify identity and makes sure its a patient
    if current_user.PatientID is None:
        raise HTTPException(status_code=403, detail="Not a patient account")
    
    # Displays information by using Patient ID as variable for the Self-Service View in Database
    results = db.query(models.PatientSelfService).filter(
        models.PatientSelfService.PatientID == current_user.PatientID
    ).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No prescriptions found")
        
    return results

# ---------------------------
# --- Reporting Endpoints ---
# ---------------------------

# Generates a detailed clinical report, showing records of patients vaccinated based on Vaccination name
@app.get("/reports/vaccination-coverage/{vaccine_type}", 
         response_model=List[schemas.VaccinationSummary], 
         tags=["Management Reports"])
def get_vaccination_report(
    vaccine_type: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
    ):

    # To ensure that patients can't see high-level clinical stats
    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Staff only access")
    
    # Complex query joining patients, vaccinations, and doctors tables in db to get a full clinical report
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
        raise HTTPException(status_code=404, detail=f"No data for {vaccine_type}")

    return results


# Provides an overview of total, pending, and dispensed prescriptions across different pharmacy locations
@app.get("/reports/facility-workload", 
         response_model=List[schemas.FacilityWorkload], 
         tags=["Management Reports"])
def get_facility_workload(
    facility_name: Optional[str] = None, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
    ):
    # Check that patients cannot use the endpoint and give a 403 error
    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Staff only access")

    # Perform query to find total counts of prescriptions and status 
    query = db.query(
        models.Facility.FacilityName,
        func.count(models.Prescription.PrescriptionID).label("TotalPrescriptions"),
        func.sum(case((models.Prescription.Status == 'Pending', 1), else_=0)).label("PendingCount"),
        func.sum(case((models.Prescription.Status == 'Dispensed', 1), else_=0)).label("DispensedCount")
    ).join(models.Prescription, models.Facility.FacilityID == models.Prescription.FacilityID)

    if facility_name:
        query = query.filter(models.Facility.FacilityName.ilike(f"%{facility_name}%"))

    results = query.group_by(models.Facility.FacilityName).all()

    if not results:
        error_msg = f"No workload data found for facility: {facility_name}" if facility_name else "No workload data found"
        raise HTTPException(status_code=404, detail=error_msg)

    return results

# -----------------------------
# --- Operational Endpoints ---
# -----------------------------

# Simultaneously creates a new patient record as well as their portal account
@app.post("/patients/register-portal", tags=["Patient Management"])
def register_patient_with_portal(
    data: schemas.PatientPortalRegistration, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Two-in-one function: Creates the patient record AND their secure login in one transaction
    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Unauthorized")

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
    db.flush() # Flushes to refresh and get the new PatientID from the User table

    # Automates new username and password generation for the patient based on pattern
    suffix = data.NHS_Number[-3:]
    generated_username = f"{data.FirstName.lower()}{suffix}"
    generated_password = f"{data.NHS_Number}{data.LastName}"
    
    # Insert records in SYSTEM_USERS table
    new_user = models.User(
        Username=generated_username,
        HashedPassword=get_password_hash(generated_password),
        RoleID=5,
        PatientID=new_patient.PatientID
    )
    db.add(new_user)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data error: NHS Number might already exist.")

    return {"message": "Success", "username": generated_username, "temp_pass": generated_password}


# Allows authorized clinical staff to issue multiple medications to a patient in a single request
@app.post("/prescriptions/issue", tags=["Clinical Operations"])
def issue_bulk_prescriptions(
    bulk_data: schemas.BulkPrescription,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    
    if current_user.RoleID == 5:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Loop thorugh list of new records
    for item in bulk_data.Items:
        # check if all medications exist in system 
        med_record = db.query(models.Medication).filter(
            models.Medication.MedicationName.ilike(item.MedicationName)
        ).first()
        if not med_record:
            raise HTTPException(status_code=404, detail=f"Medication {item.MedicationName} not found")
        
        # Add the new record into PRESCRIPTIONS table
        db.add(models.Prescription(
            PatientID=bulk_data.PatientID,
            DoctorID=bulk_data.DoctorID,
            MedicationID=med_record.MedicationID,
            FacilityID=bulk_data.FacilityID,
            DatePrescribed=datetime.now().date(),
            Status="Pending",
            DirectionsForUse=item.Directions,
            Quantity=1
        ))

    db.commit()
    return {"message": "Prescriptions issued successfully"}

# Handle the physical dispensing of medication, updates the prescription status, and automatically deducts the items from the inventory. 
@app.put("/prescriptions/{prescription_id}/dispense", tags=["Clinical Operations"])
def dispense_prescription(
    prescription_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):

    # Only Admin or Pharmacist users can access API
    if current_user.RoleID not in [1, 2]:  
        raise HTTPException(status_code=403, detail="Only Pharmacists can dispense")

    # Verify precription actually exists based on ID
    prescription = db.query(models.Prescription).filter(models.Prescription.PrescriptionID == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=400, detail="Prescription not found")
    
    # Logic check: Prevent double-dispensing
    if prescription.Status in ["Dispensed", "Collected"]:
        raise HTTPException(status_code=400, detail="This prescription has already been dispensed/collected")


    # Check the drug exists in MEDICATIONS table
    medication = db.query(models.Medication).filter(models.Medication.MedicationID == prescription.MedicationID).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found in catalog")
    
    # Doesn't dispense if the shelf is empty (Stock = 0)
    if medication.StockQuantity < prescription.Quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock for {medication.MedicationName}. Available: {medication.StockQuantity}"
        )

    try:
        # Update both the record and the inventory to maintain consistency
        prescription.Status = "Dispensed"
        prescription.DateDispensed = datetime.now().date()
        prescription.DispensingPharmacist = current_user.Username
        medication.StockQuantity -= prescription.Quantity
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction failed")

    return {"message": "Medication dispensed successfully"}


# Updating the patient records for both PATIENT and PATIENT_RECORD_LOGS after a new cnsulatation appointment.
@app.put("/patients/{patient_id}/consultation", tags=["Clinical Operations"])
def conduct_clinical_consultation(
    patient_id: int, 
    data: schemas.ClinicalConsultation, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Only Admin or Doctor allowed to access endpoint
    if current_user.RoleID not in [1, 3]:
        raise HTTPException(status_code=403, detail="Unauthorized clinical access")
    
    # If Patient ID doesnot match, retun an error response
    patient = db.query(models.Patient).filter(models.Patient.PatientID == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update Current Profile in PATIENTS table (Allergy)
    if data.NewAllergies and data.NewAllergies.strip():
        # Convert to lowercase for comparison
        input_lower = data.NewAllergies.lower()
        
        # Keywords that signal the doctor isn't actually adding a new medical allergy
        danger_keywords = ["no new", "none", "n/a", "no change", "reported", "string"]
        
        # Logic: If the input DOES NOT contain any danger keywords, proceed with update
        if not any(keyword in input_lower for keyword in danger_keywords):
            patient.Allergies = data.NewAllergies
        else:
            print(f"Update ignored: '{data.NewAllergies}' recognized as placeholder.")

    # Creating NEW entry in PATIENT_RECORDS_LOG
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


# Removes an incorrect or accidental prescription record from the system (Only before it is fulfilled).
@app.delete("/prescriptions/{prescription_id}", tags=["Clinical Operations"])
def cancel_prescription(
    prescription_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Only Admins or Doctors should be able to cancel orders
    if current_user.RoleID not in [1, 3]:
        raise HTTPException(status_code=403, detail="Only clinical staff can cancel prescriptions")

    prescription = db.query(models.Prescription).filter(
        models.Prescription.PrescriptionID == prescription_id
    ).first()

    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Safety Guard: Prevent deletion of records that are already part of a clinical audit trail
    if prescription.Status in ["Dispensed", "Collected"]:
        raise HTTPException(
            status_code=400, 
            detail="Legal Restriction: Cannot delete a prescription once it has been dispensed."
        )

    db.delete(prescription)
    db.commit()
    return {"message": f"Prescription {prescription_id} successfully removed."}

# Executes a medical recall by zeroing out stock and flagging the medication name to prevent any further dispensing.
@app.delete("/medications/{medication_id}/recall", tags=["Inventory Management"])
def recall_medication(
    medication_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Make sure only admin and pharmacist can use endpoint
    if current_user.RoleID not in [1, 2]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Checking if drug exists in MEDICINES based on ID
    medication = db.query(models.Medication).filter(models.Medication.MedicationID == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail=f"Medication with ID {medication_id} not found")
    
    # Safety Check: Can't recall if there are active prescriptions waiting in PRESCRIPTIONS table
    active_exists = db.query(models.Prescription).filter(
        models.Prescription.MedicationID == medication_id,
        models.Prescription.Status == "Pending"
    ).first()

    if active_exists:
        raise HTTPException(status_code=400, detail="Pending orders exist. Recall blocked.")

    # Logical Delete : Instead of deleting the row, zero out stock and flag it it .
    # This protects our history while preventing new orders.
    medication.StockQuantity = 0
    medication.MedicationName = f"[RECALLED] {medication.MedicationName}"
    db.commit()
    return {"message": "Recall successful"}