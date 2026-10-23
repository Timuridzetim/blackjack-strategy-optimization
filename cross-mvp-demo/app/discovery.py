"""Live destination POI discovery with OpenStreetMap. No fabricated travel prices."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import asyncio
import httpx
from .engine import PlanRequest

CACHE={}
UA='CROSS-Travel-Planner-Student-Demo/0.3 (noncommercial education; https://cross-mvp-demo.onrender.com)'
KNOWN={
    'Helsinki': (60.1699,24.9384,'Finland'),
    'Lisbon':(38.7223,-9.1393,'Portugal'),
    'Madrid':(40.4168,-3.7038,'Spain'),
    'Porto':(41.1579,-8.6291,'Portugal'),
    'Paris':(48.8566,2.3522,'France'),
    'Rome':(41.9028,12.4964,'Italy'),
    'Prague':(50.0755,14.4378,'Czechia')
}
HELSINKI_SAUNAS=[
 {'name':'Löyly Helsinki','category':'Saunas','url':'https://www.loylyhelsinki.fi/en/public-sauna','details':'Seaside wood-fired and smoke sauna · book a session', 'price_eur_pp':29, 'price_source':'Published adult admission on venue website; reconfirm for dates'},
 {'name':'Allas Pool','category':'Saunas','url':'https://www.allaspool.fi/en/','details':'Harbour pools and public saunas · check tickets and opening hours'},
 {'name':'Kotiharjun Sauna','category':'Saunas','url':'https://www.kotiharjunsauna.fi/en','details':'Traditional wood-fired neighbourhood sauna · check entry policy', 'price_eur_pp':16, 'price_source':'Published general admission on venue website; reconfirm for dates'},
 {'name':'Sompasauna','category':'Saunas','url':'https://www.myhelsinki.fi/visit/seven-ways-to-experience-sauna-in-helsinki/','details':'Community sauna maintained by visitors · check site guidance'},
]

def _pack(name,cat,url,details='',origin='OpenStreetMap',**extras):
    return {'name':name,'category':cat,'url':url,'details':details,'source':origin,**extras}

async def _load_osm(destination:str,interest_sauna:bool):
    city=destination.title()
    cached=CACHE.get((city,interest_sauna))
    if cached and cached[0]>datetime.now(timezone.utc):return cached[1]
    if city in KNOWN:lat,lon,country=KNOWN[city]
    else:
        # Nominatim has a strict per-second request policy; cache and avoid
        # unbounded requests to public volunteer infrastructure.
        async with httpx.AsyncClient(timeout=6,headers={'User-Agent':UA}) as client:
            r=await client.get('https://nominatim.openstreetmap.org/search',params={'q':destination,'format':'jsonv2','limit':1,'addressdetails':1})
            r.raise_for_status();items=r.json()
        if not items:raise LookupError('Destination was not found in OpenStreetMap')
        lat=float(items[0]['lat']);lon=float(items[0]['lon']);country=items[0].get('address',{}).get('country','')
    # The query returns named POIs only, to keep load bounded and results useful.
    # No price is read from OSM; operator websites are authoritative.
    radius=7000
    q=f'''[out:json][timeout:17];(
       nwr(around:{radius},{lat},{lon})["leisure"="sauna"]["name"];
       nwr(around:{radius},{lat},{lon})["name"~"sauna|löyly|allas",i];
       nwr(around:{radius},{lat},{lon})["tourism"~"attraction|museum"]["name"];
    );out center 75;'''
    async with httpx.AsyncClient(timeout=21,headers={'User-Agent':UA}) as client:
        r=await client.post('https://overpass.kumi.systems/api/interpreter',content=q)
        r.raise_for_status();entries=r.json()['elements']
    data=[];seen=set()
    for el in entries:
        tags=el.get('tags') or {};name=(tags.get('name:en') or tags.get('name') or '').strip()
        if not name or name.casefold() in seen:continue
        is_sauna=(tags.get('leisure')=='sauna' or 'sauna' in name.casefold() or 'löyly' in name.casefold() or 'allas' in name.casefold())
        if not is_sauna and tags.get('tourism') not in ('attraction','museum'):continue
        seen.add(name.casefold());cat='Saunas' if is_sauna else 'Culture'
        url=tags.get('website') or tags.get('contact:website') or f"https://www.openstreetmap.org/{el['type']}/{el['id']}"
        if not str(url).startswith('https://') and not str(url).startswith('http://'):url=f"https://www.openstreetmap.org/{el['type']}/{el['id']}"
        if is_sauna or len([x for x in data if x['category']=='Culture'])<7:
            data.append(_pack(name,cat,url,tags.get('description:en') or tags.get('description','')[:140],
                 origin='OpenStreetMap', osm_url=f"https://www.openstreetmap.org/{el['type']}/{el['id']}"))
    data.sort(key=lambda x:(x['category']!='Saunas' if interest_sauna else x['category']!='Culture',x['name']))
    data=data[:22]
    CACHE[(city,interest_sauna)]=(datetime.now(timezone.utc)+timedelta(hours=6),(data,country))
    return data,country

async def explore_trip(req:PlanRequest)->dict:
    now=datetime.now(timezone.utc).isoformat();sauna=any(x.lower().startswith('sauna') for x in req.interests)
    try:
        places,country=await _load_osm(req.destination,sauna)
        mode='openstreetmap_live'
        lookup_notice='Real location records from OpenStreetMap. Admissions, opening hours and availability must be confirmed with venues.'
    except (LookupError,httpx.HTTPError,ValueError,KeyError,IndexError):
        places=[];country=KNOWN.get(req.destination.title(),(0,0,''))[2]
        mode='directory_fallback'
        lookup_notice='Live place lookup is temporarily unavailable. Showing separately sourced venue links where available.'
    if req.destination.casefold()=='helsinki' and sauna:
        existing={p['name'].casefold() for p in places}
        for s in reversed(HELSINKI_SAUNAS):
            if s['name'].casefold() not in existing:
                places.insert(0,_pack(s['name'],s['category'],s['url'],s['details'],origin='Venue / MyHelsinki',**{k:v for k,v in s.items() if k.startswith('price_')}))
    places=places[:18]
    # Empty means failed search, not an opportunity to hallucinate.
    end=req.start_date+timedelta(days=req.days-1)
    days=[]
    for i in range(req.days):
        date=req.start_date+timedelta(days=i)
        relevant=([p for p in places if p['category']=='Saunas'] if sauna else []) if i==1 else []
        if not relevant:relevant=[p for p in places if p['category']!='Saunas'] if i%2==0 else places
        picks=relevant[(max(0,i-1)*2)%max(1,len(relevant)):][:2] if relevant else []
        days.append({'number':i+1,'date':date.isoformat(),'title':'Arrival and city orientation' if i==0 else ('Departure day' if i==req.days-1 else 'Explore and unwind'),
                     'stops':[{'name':p['name'],'category':p['category'],'url':p['url']} for p in picks]})
    # Only venue admission with an explicit published price may be calculated;
    # never add up guessed flights, stay, transfer or total trip cost.
    priced=[x for x in places if isinstance(x.get('price_eur_pp'),int)]
    return {'status':'discovered','mode':'live_discovery','source_type':mode,'destination':req.destination,'country':country,
        'origin':req.origin,'start_date':req.start_date.isoformat(),'end_date':end.isoformat(),'date_is_suggestion':True,
        'days':req.days,'travelers':req.travelers,'budget':req.budget,'interests':req.interests,'last_checked':now,
        'places':places,'days_preview':days,'priced_venues':priced,'count':len(places),
        'data_notice':lookup_notice,'budget_notice':'€'+f'{req.budget:,}'+' is your maximum total. Flight, hotel and transport costs are NOT quoted: no verified all-in itinerary yet.',
        'providers':[
          {'name':'Google Flights','label':'Compare flights','url':'https://www.google.com/travel/flights'},
          {'name':'Booking.com','label':'Find accommodation','url':'https://www.booking.com/searchresults.html?ss='+quote(req.destination)},
          {'name':'Google Maps','label':'Explore places','url':'https://www.google.com/maps/search/?api=1&query='+quote(req.destination+' '+('sauna' if sauna else 'attractions'))}
        ], 'attribution':'Place data © OpenStreetMap contributors (ODbL). Some venue links curated from official websites.'}
