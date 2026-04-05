from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to Oura API"}

@app.get("/products")
def get_products():
    return {
        "status": "success",
        "items": ["Bluetooth Speaker", "Home Theater", "Soundbar"]
    }
