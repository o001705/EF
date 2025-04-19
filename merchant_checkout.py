from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uuid
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    transaction_id = str(uuid.uuid4())
    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "transaction_id": transaction_id,
        "product_id": "PROD123",
        "amount": 100000,
	    "mfe_url": "http://localhost:8001/start",
        "callback_url": "http://localhost:8002/merchant/loan-callback"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("merchant_checkout:app", host="0.0.0.0", port=8000, reload=True)
