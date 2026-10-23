"""Deterministic, budget-constrained optimizer for reproducible CROSS demos.

All offer catalog data is fictional. The engine is source-agnostic, so an approved
supplier adapter can pass current provider-quoted prices into the same optimizer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations
from math import ceil
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .catalog import CITIES


class PlanRequest(BaseModel):
    origin: str = Field(default="Madrid", min_length=2, max_length=70)
    destination: str = Field(default="Lisbon", min_length=2, max_length=70)
    start_date: date = Field(default_factory=lambda: date.today()+timedelta(days=28))
    days: int = Field(default=5, ge=2, le=14)
    travelers: int = Field(default=2, ge=1, le=8)
    budget: int = Field(default=700, ge=100, le=20000)
    preference: Literal["balanced", "comfort", "save"] = "balanced"
    interests: list[str] = Field(default_factory=lambda: ["Culture", "Views"])
    message: str = Field(default="", max_length=500)

    @field_validator("destination")
    @classmethod
    def normalize_destination(cls, v: str) -> str:
        for key in CITIES:
            if v.strip().casefold() == key.casefold():
                return key
        return v.strip().title()


@dataclass(frozen=True)
class Candidate:
    transport: dict
    stay: dict
    selected: tuple[str, ...]
    total: int
    transport_total: int
    stay_total: int
    transit_total: int
    activity_total: int
    reserve: int
    score: float
    quality: int


CATEGORIES = {"Culture", "Views", "History", "Food", "Outdoors", "Local life"}


def parse_message(message: str, current: dict | None = None) -> dict:
    """Convenience parser. Does not invent cities or future dates.

    Interprets only explicitly supplied and uniquely recognizable values.
    Manual fields always remain editable before submitting a plan.
    """
    out = dict(current or {})
    if not message.strip():
        return out
    low = message.lower()
    for city in CITIES:
        if re.search(r"\b"+re.escape(city.lower())+r"\b", low):
            out["destination"] = city
            break
    origin = re.search(r"\bfrom\s+([a-zÀ-ÿ\s-]+?)\s+to\s+[a-zÀ-ÿ-]+\b",message,re.I)
    if origin:
        out["origin"] = origin.group(1).strip().title()[:70]
    bm = re.search(r"(?:€\s*|eur\s*|under\s+€?\s*)(\d[\d,]*)\b",low)
    if not bm:
        bm = re.search(r"\b(\d[\d,]*)\s*(?:euros|eur)\b",low)
    if bm:
        raw=int(bm.group(1).replace(",",""))
        if 100<=raw<=20000:
            out["budget"] = raw
    dm = re.search(r"\b(\d{1,2})\s*(?:-|\s)?(?:day|days|night|nights)\b",low)
    if dm:
        raw=int(dm.group(1));out["days"] = min(14,max(2,raw+int("night" in dm.group(0))))
    pm = re.search(r"\bfor\s+(\d)\s+(?:people|persons|travellers|travelers|adults)\b",low)
    if pm:
        out["travelers"] = int(pm.group(1))
    return out


def activity_power(item: dict, interests: list[str]) -> float:
    return float(item["score"]) + (3.3 if item["category"] in interests else 0.0)


def _candidates(req: PlanRequest) -> list[Candidate]:
    city=CITIES[req.destination]
    n=req.days-1
    reserve=max(25,round(req.budget*0.07))
    transit=city["transit_pp"]*req.travelers
    mandatory=[a for a in city["activities"] if a["pp"]==0]
    optional=[a for a in city["activities"] if a["pp"]>0]
    out=[]
    for transport in city["transport"]:
        for stay in city["stays"]:
            tr=(transport["pp"]+transport["fees_pp"])*req.travelers
            lodging=(stay["night"]*n)+stay["fees"]
            fixed=tr+lodging+transit+reserve
            if fixed>req.budget:
                continue
            for k in range(len(optional)+1):
                for subset in combinations(optional,k):
                    activities_cost=sum(a["pp"]*req.travelers for a in subset)
                    total=fixed+activities_cost
                    if total>req.budget:
                        continue
                    selected=tuple(a["id"] for a in (mandatory+list(subset)))
                    activity_quality=sum(activity_power(a,req.interests) for a in mandatory+list(subset))
                    quality=int(stay["quality"]*3+transport["quality"]*1.5+activity_quality)
                    score=(stay["quality"]*4.0+transport["quality"]*2.1+activity_quality*1.35
                           - 0.025*total)
                    out.append(Candidate(transport,stay,selected,total,tr,lodging,transit,activities_cost,reserve,score,quality))
    return out


def pick_variants(candidates: list[Candidate], preference: str = "balanced") -> list[tuple[str, Candidate]]:
    if not candidates:
        return []
    variants=[]; used=set()
    specs=[
        ("Best fit",lambda c:c.score),
        ("Lowest cost",lambda c:-c.total+0.0001*c.quality),
        ("More comfort",lambda c:c.stay["quality"]*14+c.transport["quality"]*9+c.quality*0.12-0.008*c.total),
    ]
    order = {"balanced":[0,1,2], "save":[1,0,2], "comfort":[2,0,1]}[preference]
    for pos in order:
        label,key = specs[pos]
        for candidate in sorted(candidates,key=key,reverse=True):
            sig=(candidate.transport["id"],candidate.stay["id"],candidate.selected)
            if sig not in used:
                used.add(sig);variants.append((label,candidate));break
    return variants


def build_days(req: PlanRequest, activities: list[dict]) -> list[dict]:
    city=CITIES[req.destination]
    free=[a for a in activities if a["pp"]==0]
    paid=[a for a in activities if a["pp"]>0]
    ordered=free+paid
    result=[]
    for i in range(req.days):
        thisdate=req.start_date+timedelta(days=i)
        title="Arrival & first impressions" if i==0 else ("One last look" if i==req.days-1 else ["City discoveries","Local favorites","Culture & views","Slow city day"][min(3,(i-1)%4)])
        stops=[]
        if i==0:
            stops.append({"time":"11:30","title":f"Arrive in {req.destination}","detail":"Travel to the city and drop your bags", "kind":"travel","pp":0})
            stops.append({"time":"14:00","title":"Check in & settle", "detail":"Leave time for getting oriented", "kind":"stay","pp":0})
        if i==req.days-1:
            stops.append({"time":"10:00","title":"Coffee & neighborhood walk","detail":city["moments"][i%len(city["moments"])], "kind":"free","pp":0})
            stops.append({"time":"15:00","title":"Return journey", "detail":"Leave time for transfer and security", "kind":"travel","pp":0})
        if i<req.days-1:
            # Distribute activities across visit days, allowing >1/day as required.
            alloc=[(j,a) for j,a in enumerate(ordered) if j%max(req.days-1,1)==i]
            for k,(j,a) in enumerate(alloc):
                stops.append({"time":["10:00","13:30","17:30"][k%3],"title":a["name"],"detail":f'{a["category"]} · {a["duration"]}',"kind":"paid" if a["pp"] else "free","pp":a["pp"]})
            if not alloc and i>0:
                stops.append({"time":"11:00","title":"Explore at your own pace","detail":city["moments"][i%len(city["moments"])],"kind":"free","pp":0})
        result.append({"number":i+1,"date":thisdate.isoformat(),"weekday":thisdate.strftime("%a"),"title":title,"stops":stops})
    return result


def format_candidate(req: PlanRequest, label: str, c:Candidate, index:int) -> dict:
    city=CITIES[req.destination]
    acts=[a for a in city["activities"] if a["id"] in c.selected]
    pieces=[
        {"key":"transport","label":"Return travel","amount":c.transport_total,"detail":f'{req.travelers} × ({c.transport["pp"]} + €{c.transport["fees_pp"]} fees)'},
        {"key":"stay","label":f'Stay · {req.days-1} nights',"amount":c.stay_total,"detail":f'€{c.stay["night"]}/night + €{c.stay["fees"]} mandatory fees'},
        {"key":"activities","label":"Activities","amount":c.activity_total,"detail":"Selected ticketed activities"},
        {"key":"transit","label":"Local transport","amount":c.transit_total,"detail":f'€{city["transit_pp"]} per traveler'},
        {"key":"reserve","label":"Budget reserve","amount":c.reserve,"detail":"Set aside, not charged by CROSS"},
    ]
    return {
        "id":f"route-{index}","label":label,"total":c.total,"remaining":req.budget-c.total,
        "transport":{"id":c.transport["id"],"name":c.transport["name"],"mode":c.transport["mode"],"duration":c.transport["duration"],"detail":c.transport["detail"],"amount":c.transport_total},
        "stay":{"id":c.stay["id"],"name":c.stay["name"],"detail":c.stay["detail"],"amount":c.stay_total,"nights":req.days-1},
        "activities":acts,"breakdown":pieces,"days":build_days(req,acts),"quality":c.quality,
        "notes":["Numbers are sample demo inventory, not bookable quotes.","Booking links open independent supplier search pages; confirm final prices there."]
    }


def plan_trip(req:PlanRequest)->dict:
    from datetime import datetime,timezone
    available=_candidates(req)
    formatted=[format_candidate(req,label,c,i) for i,(label,c) in enumerate(pick_variants(available,req.preference))]
    cheapest_req=PlanRequest(**{**req.model_dump(),"budget":20000})
    cheapest=min(_candidates(cheapest_req), key=lambda c:c.total,default=None)
    city=CITIES[req.destination]
    return {
        "status":"ready" if formatted else "over_budget", "mode":"demo",
        "source_type":"synthetic_catalog", "last_checked":datetime.now(timezone.utc).isoformat(),
        "data_notice":"Illustrative demo prices. Not live, verified or bookable. Confirm availability and total on supplier websites.",
        "destination":req.destination,"country":city["country"],"origin":req.origin,
        "start_date":req.start_date.isoformat(),"end_date":(req.start_date+timedelta(days=req.days-1)).isoformat(),
        "days":req.days,"travelers":req.travelers,"budget":req.budget,
        "city":{"tagline":city["tagline"],"accent":city["accent"],"accent2":city["accent2"],"theme":city["theme"]},
        "alternatives":formatted,
        "lowest_possible":cheapest.total if cheapest else None,
        "estimated_shortfall":max(0,cheapest.total-req.budget) if cheapest else None,
        "providers":[
            {"name":"Google Flights","category":"flight search","url":"https://www.google.com/travel/flights"},
            {"name":"Booking.com","category":"stays search","url":"https://www.booking.com"},
            {"name":"GetYourGuide","category":"activities search","url":"https://www.getyourguide.com"},
        ],
    }
