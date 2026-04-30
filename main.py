from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database

app = FastAPI(title="MedCare API")

@app.get("/")
def read_root():
    return {"message": "MedCare API is live and running in Docker!"}