# File 3: Bank Micro Frontend (Bank MFE App)
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="Bank Micro Frontend App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BANK_BACKEND = "http://localhost:8003"
MERCHANT_CALLBACK = "http://localhost:8002/merchant/loan-callback"

# In-memory transaction state
transaction_store = {}

@app.post("/start", response_class=HTMLResponse)
async def start_session(
    request: Request,
    transaction_id: str = Form(...),
    product_id: str = Form(...),
    amount: str = Form(...),  # Accept as str for better error handling
    callback_url: str = Form(...)
):
    try:
        amount_float = float(amount)
    except ValueError:
        amount_float = 0.0  # or raise HTTPException if this is critical

    print("Transaction ID in Start = ", transaction_id)

    MERCHANT_CALLBACK = callback_url  # Update the callback URL dynamically

    return templates.TemplateResponse("phone_input.html", {
        "request": request,
        "transaction_id": transaction_id,
        "product_id": product_id,
        "amount": amount_float,
        "callback_url": callback_url
    })

@app.post("/process-phone")
async def process_phone(request: Request, phone: str = Form(...), transaction_id: str = Form(...), product_id: str = Form(...), amount: float = Form(...)):
    transaction_store[transaction_id] = {"phone": phone, "amount": amount}

    print("Transaction ID in Process_Phone  = ", transaction_id)
    async with httpx.AsyncClient() as client:
        customer_response = await client.get(f"{BANK_BACKEND}/bank/get-customer/{phone}")

        if customer_response.status_code == 200:
            offers_response = await client.get(f"{BANK_BACKEND}/bank/get-personalized-offers", params={"phone_number": phone})
            offers = offers_response.json()
            return templates.TemplateResponse("offers.html", {"request": request, "offers": offers, "transaction_id": transaction_id})
        else:
            return templates.TemplateResponse("kyc_form.html", {"request": request, "phone": phone, "transaction_id": transaction_id, "amount": amount})

@app.post("/process-kyc")
async def process_kyc(request: Request, phone: str = Form(...), govt_id: str = Form(...), name: str = Form(...), address: str = Form(...), transaction_id: str = Form(...), amount: float = Form(...)):
    async with httpx.AsyncClient() as client:
        kyc_data = {"phone_number": phone, "govt_id": govt_id, "name": name, "address": address}
        print("Processing KYC...", kyc_data)
        await client.post(f"{BANK_BACKEND}/bank/invoke-kyc", json=kyc_data)
        print("KYC processed successfully.")
        print("Invoking credit bureau...")
        score_res = await client.post(f"{BANK_BACKEND}/bank/invoke-credit-bureau", json=kyc_data)
        credit_score = score_res.json().get("credit_score")
        print("Credit score received:", credit_score)

        onboard_data = {
            "phone_number": phone,
            "name": name,
            "credit_score": credit_score,
            "kyc_verified": True
        }
        await client.post(f"{BANK_BACKEND}/bank/onboard-customer", json=onboard_data)

        offers_res = await client.get(f"{BANK_BACKEND}/bank/get-loan-offers", params={"phone_number": phone, "amount": amount})
        offers = offers_res.json()

        if not offers:
            print("No eligible loan offers found.")
            async with httpx.AsyncClient() as client:
                status = 'failure'
                callback_payload = {"transaction_id": transaction_id, "status": status, "callback_url": MERCHANT_CALLBACK}
                await client.post(f"{BANK_BACKEND}/bank/notify-merchant", json=callback_payload)
            
                return templates.TemplateResponse("completion.html", {
                    "request": request,
                    "status": "No eligible loan offers found. Merchant notified.",
                    "transaction_id": transaction_id
                })

        return templates.TemplateResponse("offers.html", {"request": request, "offers": offers, "transaction_id": transaction_id})

@app.post("/accept-offer")
async def accept_offer(request: Request, offer_id: str = Form(...), transaction_id: str = Form(...)):
    txn = transaction_store.get(transaction_id)
    phone = txn["phone"]
    amount = txn["amount"]

    print("Transaction ID in accept-offer  = ", transaction_id)

    loan_req = {"offer_id": offer_id, "amount": amount, "phone_number": phone}

    async with httpx.AsyncClient() as client:
        loan_res = await client.post(f"{BANK_BACKEND}/bank/originate-loan", json=loan_req)
        status = loan_res.json().get("status")

        status = 'success' if status == "Loan Originated" else 'failure'

        print("Transaction ID in notify_merchant  = ", transaction_id)

        callback_payload = {"transaction_id": transaction_id, "status": status, "callback_url": MERCHANT_CALLBACK}
        await client.post(f"{BANK_BACKEND}/bank/notify-merchant", json=callback_payload)

    return templates.TemplateResponse("completion.html", {"request": request, "status": status, "transaction_id": transaction_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bank_mfe:app", host="0.0.0.0", port=8001, reload=True)
