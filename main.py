from fastapi import FastAPI

app = FastAPI(title="Pharmacy Management System API")

@app.get("/")
def read_root():
    return {"message": "Pharmacy API is live and running in Docker!"}