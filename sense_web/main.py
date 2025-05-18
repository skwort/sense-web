from fastapi import FastAPI
from sense_web.api import api_router

app = FastAPI(title="Sense Web - CoAP-HTTP Gateway")
app.include_router(api_router)
