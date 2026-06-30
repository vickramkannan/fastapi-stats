from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import jwt
import time
import uuid
import os


EMAIL = "22f3000616@ds.study.iitm.ac.in"

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_headers(request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = (
        f"{time.perf_counter() - start:.6f}"
    )

    return response


# ---------------- STATS ----------------

@app.get("/stats")
async def stats(values: str = Query(...)):

    try:
        nums = [int(x) for x in values.split(",")]

        return {
            "email": EMAIL,
            "count": len(nums),
            "sum": sum(nums),
            "min": min(nums),
            "max": max(nums),
            "mean": sum(nums) / len(nums),
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid values"
        )


# ---------------- VERIFY JWT ----------------


PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""


ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-jqikaik5.apps.exam.local"


class TokenRequest(BaseModel):
    token: str



@app.post("/verify")
async def verify(req: TokenRequest):

    try:
        payload = jwt.decode(
            req.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }


    except jwt.InvalidTokenError:
        return JSONResponse(
            status_code=401,
            content={"valid": False}
        )



# ---------------- ANALYTICS ----------------


class AnalyticsRequest(BaseModel):
    events: list



API_KEY = "ak_45rln8w59kkg9sgnszl8ogsj"



@app.post("/analytics")
async def analytics(
    request: Request,
    req: AnalyticsRequest
):

    key = request.headers.get("X-API-Key")

    if key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


    users = set()
    revenue = 0
    counts = {}


    for event in req.events:

        user = event.get("user_id")

        if user:
            users.add(user)
            counts[user] = counts.get(user, 0) + 1


        if event.get("type") == "purchase":
            revenue += event.get(
                "amount",
                0
            )


    top_user = None

    if counts:
        top_user = max(
            counts,
            key=counts.get
        )


    return {
        "email": EMAIL,
        "total_events": len(req.events),
        "unique_users": len(users),
        "revenue": revenue,
        "top_user": top_user
    }



# ---------------- CONFIG ----------------


@app.get("/effective-config")
async def effective_config(request: Request):

    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }


    # yaml override
    config["port"] = 8732
    config["log_level"] = "warning"


    # env override
    config["workers"] = 6


    if os.getenv("APP_WORKERS"):
        config["workers"] = int(
            os.getenv("APP_WORKERS")
        )


    if os.getenv("APP_API_KEY"):
        config["api_key"] = os.getenv("APP_API_KEY")


    # query override
    for item in request.query_params.getlist("set"):

        if "=" not in item:
            continue

        key, value = item.split("=", 1)


        if key in ["port", "workers"]:
            config[key] = int(value)

        elif key == "debug":
            config[key] = value.lower() in [
                "true",
                "1",
                "yes",
                "on"
            ]

        else:
            config[key] = value



    config["api_key"] = "****"


    return config
