import random
from fastapi import Body, FastAPI, HTTPException
import httpx
from pydantic import BaseModel
from typing import Dict
from jose import jwt
import uuid

app = FastAPI(title="Bank Backend Service")

# Simulated databases
customer_db: Dict[str, Dict] = {
    "1234567890": {
        "name": "John Doe",
        "govt_id": "ID123456789",	
        "phone_number": "1234567890",
        "credit_score": 700,
        "kyc_verified": True 
    },
    "9876543210": {
        "name": "Jane Smith",
        "govt_id": "ID9876543210",	
        "phone_number": "9876543210",
        "credit_score": 650,
        "kyc_verified": True 
    },
    "1122334455": {
        "name": "Alice Johnson",
        "govt_id": "ID1122334455",
        "phone_number": "1122334455",
        "credit_score": 720,
        "kyc_verified": True 
    },
    "5566778899": {
        "name": "Bob Brown",
        "govt_id": "ID566778899",
        "phone_number": "5566778899",
        "credit_score": 680,
        "kyc_verified": True 
    }
}
credit_score_db: Dict[str, int] = {
    "1234567890": 700,
    "9876543210": 650,
    "1122334455": 720,
    "5566778899": 680,
    "9999999999": 800,
    "8888888888": 600,
    "7777777777": 750,
    "6666666666": 620,
    "5555555555": 690,
    "4444444444": 710,
    "3333333333": 730,
    "2222222222": 740,
    "1111111111": 760,
    "0000000000": 500
}
offers_db: Dict[int, str] = {
    1: "Offer 1: Low Interest EMI",
    2: "Offer 2: Cashback Offer",
    3: "Offer 3: No Cost EMI"
}
loyalty_points_db: Dict[str, int] = {
    "1234567890": 1000,
    "9876543210": 500,
    "1122334455": 800,
    "5566778899": 300
}

SECRET_KEY = "merchant_secret_key"
ALGORITHM = "HS256" # Replace with your actual algorithm
EXPIRATION_TIME = 3600 # Token expiration time in seconds

class Customer(BaseModel):
    phone_number: str
    name: str
    govt_id: str
    credit_score: int
    kyc_verified: bool

class KYCRequest(BaseModel):
    phone_number: str
    govt_id: str
    name: str
    address: str

class LoanRequest(BaseModel):
    offer_id: str
    amount: float
    phone_number: str

class CallbackPayload(BaseModel):
    transaction_id: str
    status: str
    callback_url: str

class Offer(BaseModel):
    offer_id: int
    description: str

@app.get("/bank/get-customer/{phone_number}")
async def get_customer(phone_number: str):
    if phone_number in customer_db:
        return customer_db[phone_number]
    raise HTTPException(status_code=404, detail="Customer not found")

@app.post("/bank/invoke-kyc")
async def invoke_kyc(kyc_data: KYCRequest):
    customer_db[kyc_data.phone_number] = {
        "govt_id": kyc_data.govt_id,
        "name": kyc_data.name,
        "address": kyc_data.address,
        "kyc_verified": True
    }
    return {"status": "KYC Success"}

@app.post("/bank/invoke-credit-bureau")
async def invoke_credit_bureau(kyc_data: KYCRequest):
    if kyc_data.phone_number in credit_score_db:
        credit_score = credit_score_db[kyc_data.phone_number]
    else:
        credit_score = random.randint(400, 750)
        credit_score_db[kyc_data.phone_number] = credit_score  # Save for future lookups
    return {"credit_score": credit_score}

@app.get("/bank/get-loan-offers")
async def get_loan_offers(phone_number: str, amount: float):
    score = credit_score_db.get(phone_number, 700)
    if score < 550:
        return {}  # No offers for low credit score
    offer_ids = [1, 2] if score >= 750 else [2, 3]
    return [{"offer_id": oid, "description": offers_db[oid]} for oid in offer_ids]

@app.get("/bank/get-personalized-offers")
async def get_personalized_offers(phone_number: str):
    points = loyalty_points_db.get(phone_number, 0)
    base_offers = await get_loan_offers(phone_number, amount=10000)
    offers = base_offers
    if points > 800:
        offers.append({"offer_id": 4, "description": "Loyalty Bonus EMI Offer"})
    return offers

@app.get("/bank/get-loyalty-points")
async def get_loyalty_points(phone_number: str):
    return {"points": loyalty_points_db.get(phone_number, 0)}

@app.post("/bank/onboard-customer")
async def onboard_customer(customer: Customer):
    customer_db[customer.phone_number] = customer.dict()
    credit_score_db[customer.phone_number] = customer.credit_score
    return {"status": "Customer onboarded"}

@app.post("/bank/originate-loan")
async def originate_loan(loan: LoanRequest):
    if loan.phone_number in customer_db:
        return {"status": "Loan Originated"}
    return {"status": "Loan Failed"}

@app.post("/bank/notify-merchant")
async def notify_merchant(payload: CallbackPayload = Body(...)):
    print(f"[CALLBACK RECEIVED] Transaction: {payload.transaction_id} | Status: {payload.status}")	

    # Generate JWT
    jwt_token = jwt.encode(payload.model_dump(), SECRET_KEY, algorithm=ALGORITHM)

    headers = {"Authorization": f"Bearer {jwt_token}"}
    callback_url = payload.callback_url  # Make sure CallbackPayload includes this field

    # Call merchant callback URL with JWT in Authorization header
    async with httpx.AsyncClient() as client:
        response = await client.post(callback_url, json=payload.model_dump(), headers=headers)

    return {"message": "Merchant notified", "merchant_response": response.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bank_backend:app", host="0.0.0.0", port=8003, reload=True)
