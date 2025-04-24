from fastapi import Depends, FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Bearer scheme
bearer_scheme = HTTPBearer()

class CallbackPayload(BaseModel):
    transaction_id: str
    status: str
    callback_url: str


SECRET_KEY = "merchant_secret_key"
ALGORITHM = "HS256"  # Replace with your actual algorithm

# Store transaction status in memory
transaction_status_store = {}

# Verify JWT
def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/merchant/loan-callback")
async def loan_callback(payload: CallbackPayload, token_data: dict = Depends(verify_jwt)):
    print(f"[CALLBACK RECEIVED] Transaction: {payload.transaction_id} | Status: {payload.status}")
    transaction_status_store[payload.transaction_id] = payload.status
    return {"message": "Callback received and status updated"}

@app.post("/merchant/status")
async def get_status(request: Request):
    try:
        data = await request.json()
        txn_id = data.get("txn_id")
        
        status = transaction_status_store.get(txn_id)
        if status:
            return {"transaction_id": txn_id, "status": status}
        else:
            return {"transaction_id": txn_id, "status": "PENDING"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Invalid request format"})
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("merchant_callback:app", host="0.0.0.0", port=8002, reload=True)
