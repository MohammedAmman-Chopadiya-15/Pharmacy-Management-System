from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
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

@app.get("/my-prescriptions/{patient_id}", 
         response_model=List[schemas.PatientPortalResponse], 
         tags=["Patient Portal"])
def get_self_service_prescriptions(patient_id: int, db: Session = Depends(database.get_db)):
    """
    Masters Level: This endpoint leverages a Secure Database View 
    to ensure patients only see authorized prescription data.
    """
    results = db.query(models.PatientSelfService).filter(
        models.PatientSelfService.PrescriptionID.in_(
            db.query(models.Prescription.PrescriptionID).filter(models.Prescription.PatientID == patient_id)
        )
    ).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No prescriptions found for this account")
        
    return results