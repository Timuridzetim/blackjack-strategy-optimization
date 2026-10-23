"""CROSS demo travel planner. Static front end + REST API in one FastAPI process."""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .catalog import CITIES
from .intent import parse_intent
from .discovery import explore_trip, _load_live
from .engine import PlanRequest, parse_message, plan_trip

BASE=Path(__file__).parent
app=FastAPI(title="CROSS — Budget-first travel agent",version="0.1.0",docs_url="/api/docs",openapi_url="/api/openapi.json")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")

@app.get("/")
def index():
    return FileResponse(BASE/"static"/"index.html")

@app.get("/api/health")
def health():
    return {"ok":True,"brand":"CROSS","inventory":"live multi-source place discovery; no live flight or hotel quotes", "llm_available": bool(os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))}

@app.get("/api/config")
def config():
    return {"destinations":[{"name":name,"country":value["country"],"tagline":value["tagline"]} for name,value in CITIES.items()],
            "mode":"multi_source_discovery","free_to_user":True,"live_inventory":False, "llm_configured": bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")),
            "pricing_message":"Sample estimates only; no live inventory or price lock."}

class ParseRequest(BaseModel):
    message: str = Field(min_length=1,max_length=500)
    current: dict = Field(default_factory=dict)

@app.post("/api/parse")
async def parse(req:ParseRequest):
    return await parse_intent(req.message,req.current)


@app.get("/api/preview")
async def preview(destination: str, interest: str = "Culture"):
    """Read-only live-source QA: discover any location without making a booking."""
    if not 2 <= len(destination) <= 70 or not 1 <= len(interest) <= 45:
        raise HTTPException(status_code=422, detail="Invalid destination or interest")
    found = await _load_live(destination, [interest])
    return {"destination":destination,"interest":interest,"source_type":found["source_type"],
            "count":len(found["places"]),"examples":found["places"][:5],
            "search_only":found["source_type"]=="search_only"}

@app.post("/api/plan")
async def plan(req:PlanRequest):
    # Real discovery by default for *all* cities; never silently fall back to synthetic flight prices.
    return await explore_trip(req)

class DescribeRequest(BaseModel):
    request:PlanRequest
    itinerary:dict

@app.post("/api/describe")
async def describe(req:DescribeRequest):
    """Optionally use any OpenAI-compatible endpoint for editorial text only.

    Itinerary prices are entirely server computed; model cannot change them.
    No default external API call is made.
    """
    trip=req.itinerary
    if not trip or "total" not in trip or "breakdown" not in trip:
        raise HTTPException(status_code=400,detail="A computed itinerary is required")
    if not os.getenv("LLM_API_KEY"):
        return {"mode":"local","text":f"{trip.get('label','Your trip')} brings return travel, your stay, local transport and activities together. The €{trip['total']} demo total includes a reserve and leaves €{trip.get('remaining',0)} below your limit. Check live offers with the providers before booking."}
    import httpx
    base=os.getenv("LLM_BASE_URL","https://api.openai.com/v1").rstrip("/")
    model=os.getenv("LLM_MODEL","gpt-4o-mini")
    prompt=("Write a confident, concise travel-planning summary of 2–3 sentences for CROSS. "
            "The numbers given are SAMPLE prices; do not invent, verify, guarantee or replace prices. "
            "Do not claim affiliate partnerships or cashback. Emphasize user's firm budget and choice. "
            f"Trip: {req.request.origin} to {req.request.destination}, {req.request.days} days, "
            f"{req.request.travelers} people; demo quote €{trip['total']}, headroom €{trip.get('remaining',0)}; "
            f"transport: {trip.get('transport',{}).get('name')}; stay: {trip.get('stay',{}).get('name')}.")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            res=await client.post(base+"/chat/completions",headers={"Authorization":"Bearer "+os.environ["LLM_API_KEY"]},json={"model":model,"messages":[{"role":"system","content":"You write travel copy. Never hallucinate prices or bookings."},{"role":"user","content":prompt}],"temperature":0.4,"max_tokens":160})
            res.raise_for_status()
            txt=res.json()["choices"][0]["message"]["content"]
        return {"mode":"llm","text":txt}
    except (ValueError,KeyError,httpx.HTTPError):
        return {"mode":"fallback","text":"Your entire itinerary is optimized against one firm budget. Review the costs and compare your options before you book."}
