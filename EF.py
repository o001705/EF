# Purpose: Compare Monolith vs Composable Architecture in Embedded Finance
# Language: Python (FastAPI for modularity and microservices)
# Use case: Loan offering at checkout with composable building blocks

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Composable vs Monolith Embedded Finance Demo")

# -----------------------------
# MONOLITHIC IMPLEMENTATION
# -----------------------------

@app.post("/monolith/checkout")
async def monolith_checkout(customer: dict):
    # All logic crammed into a single service
    if not customer.get("kyc_done"):
        raise HTTPException(status_code=400, detail="KYC not completed")

    if customer.get("credit_score", 0) < 600:
        raise HTTPException(status_code=403, detail="Credit score too low")

    offers = [
        {
            "bank": "BankA",
            "interest_rate": 11.5,
            "tenure_months": 12,
            "emi_amount": 1100,
            "deep_link": f"https://banka.com/apply?cust_id={customer['id']}"
        },
        {
            "bank": "BankB",
            "interest_rate": 10.2,
            "tenure_months": 18,
            "emi_amount": 850,
            "deep_link": f"https://bankb.com/apply?cust_id={customer['id']}"
        }
    ]

    return {
        "message": "Choose from available offers",
        "offers": offers
    }

# -----------------------------
# COMPOSABLE IMPLEMENTATION
# -----------------------------

class Customer(BaseModel):
    id: str
    name: str
    credit_score: int
    kyc_done: bool
    loyalty_points: Optional[int] = 0

class LoanOption(BaseModel):
    bank: str
    interest_rate: float
    tenure_months: int
    emi_amount: float
    deep_link: str

# Microservice 1: KYC Service
@app.post("/kyc/verify")
async def verify_kyc(customer: Customer):
    if not customer.kyc_done:
        raise HTTPException(status_code=400, detail="KYC not completed")
    return {"status": "verified"}

# Microservice 2: Credit Decision Engine
@app.post("/credit/check")
async def credit_check(customer: Customer):
    if customer.credit_score < 600:
        raise HTTPException(status_code=403, detail="Credit score too low")
    return {"status": "eligible"}

# Microservice 3: Loyalty Discount Engine
@app.post("/loyalty/apply")
async def apply_loyalty_discount(customer: Customer):
    discount = (customer.loyalty_points or 0) * 0.01
    return {"discount_rate": min(discount, 1.0)}  # cap at 1%

# Microservice 4: Loan Offer Aggregator
@app.post("/offers/get", response_model=List[LoanOption])
async def get_offers(customer: Customer):
    loyalty_discount = await apply_loyalty_discount(customer)
    base_offers = [
        {"bank": "BankA", "interest_rate": 11.5},
        {"bank": "BankB", "interest_rate": 10.2},
        {"bank": "BankC", "interest_rate": 9.8}  # Composable advantage
    ]
    offers = []
    for o in base_offers:
        final_rate = o["interest_rate"] - loyalty_discount["discount_rate"]
        tenure = 12
        principal = 12000
        emi = (principal * (1 + final_rate * tenure / 1200)) / tenure
        offers.append(
            LoanOption(
                bank=o["bank"],
                interest_rate=round(final_rate, 2),
                tenure_months=tenure,
                emi_amount=round(emi, 2),
                deep_link=f"https://{o['bank'].lower()}.com/apply?cust_id={customer.id}"
            )
        )
    return offers

# Microservice 5: QR Code Generator
@app.post("/qr/generate")
async def generate_qr(customer: Customer):
    return {
        "qr_code": f"https://finqr.com/offers?cust_id={customer.id}&merchant=XYZ"
    }

# Composable Flow Orchestrator
@app.post("/composable/checkout")
async def checkout(customer: Customer):
    await verify_kyc(customer)
    await credit_check(customer)
    offers = await get_offers(customer)
    return {
        "message": "Choose from personalized offers with loyalty benefit",
        "offers": offers
    }

# Experience Simulator: Customer at two merchants
@app.post("/simulate/customer-experience")
async def simulate_customer_journey(customer: Customer):
    try:
        monolith_response = await monolith_checkout(customer.dict())
    except HTTPException as e:
        monolith_response = {"error": e.detail}

    try:
        await verify_kyc(customer)
        await credit_check(customer)
        offers = await get_offers(customer)
        composable_response = {
            "message": "Personalized offers available",
            "offers": offers
        }
    except HTTPException as e:
        composable_response = {"error": e.detail}

    return {
        "merchant_A_monolith": monolith_response,
        "merchant_B_composable": composable_response
    }

# invoke using http://localhost:8000/docs
# -----------------------------
# BENEFITS OF COMPOSABLE DESIGN
# -----------------------------
# 1. Services like /kyc/verify and /credit/check can be reused in other journeys.
# 2. Easily plug in a new bank offer engine without touching other logic.
# 3. Loyalty points can be integrated as optional enhancer service.
# 4. QR code-based access supports offline scan & go financing.
# 5. Flexible integration for merchants and rapid testing of new features.


if __name__ == "__main__":
    uvicorn.run("EF:app", host="0.0.0.0", port=8000, reload=True)