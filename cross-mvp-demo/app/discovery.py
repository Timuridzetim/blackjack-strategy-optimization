"""Generic live city/activity discovery. No curated city inventory, no invented prices.

Sources: OpenStreetMap via Nominatim/Photon + independent Overpass mirrors;
Wikimedia geolocated encyclopedia entries and keyword search. All network access
is bounded, deduplicated and cached; errors degrade to *search links*, not fake POIs.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import httpx

from .engine import PlanRequest

logger = logging.getLogger(__name__)
UA = 'CROSS-MVP/0.4 (https://cross-mvp-demo.onrender.com; student travel research)' 
HEADERS = {'User-Agent': UA, 'Accept': 'application/json'}
OVERPASS = ('https://overpass-api.de/api/interpreter',
            'https://overpass.private.coffee/api/interpreter')
WIKI = 'https://en.wikipedia.org/w/api.php'
CACHE: dict[tuple[str, tuple[str, ...]], tuple[float, dict]] = {}
GEO_CACHE: dict[str, tuple[float, tuple[float,float,str]]] = {}

# Interest mapping is global. Unknown custom interests still use keyword search.
TAXONOMY = {
 'Saunas': [('leisure','sauna'),('name~','sauna|löyly|bathhouse')],
 'Temples': [('amenity','place_of_worship'),('building','temple'),('historic','shrine')],
 'Spas': [('leisure','spa'),('leisure','sauna'),('tourism','spa_resort')],
 'Food': [('amenity~','restaurant|cafe|food_court|marketplace')],
 'Museums': [('tourism','museum'),('tourism','gallery')],
 'Culture': [('tourism~','museum|gallery|attraction'),('historic~','castle|monument|fort|ruins|archaeological_site')],
 'History': [('historic~','castle|monument|fort|ruins|city_gate|memorial')],
 'Architecture': [('historic~','castle|monument|manor|building'),('tourism','attraction')],
 'Views': [('tourism','viewpoint'),('natural','peak')],
 'Outdoors': [('leisure~','park|nature_reserve|garden'),('tourism','viewpoint')],
 'Hiking': [('route','hiking'),('tourism','viewpoint'),('natural','peak')],
 'Beaches': [('natural','beach'),('leisure','beach_resort')],
 'Nightlife': [('amenity~','bar|pub|nightclub')],
 'Shopping': [('shop~','mall|department_store'),('amenity','marketplace')],
 'Music': [('amenity~','theatre|arts_centre|music_venue')],
 'Sports': [('leisure~','sports_centre|stadium|swimming_pool')],
}
DEFAULT_TAGS=[('tourism~','museum|attraction|viewpoint'),('historic~','castle|monument'),('leisure','park')]
INTEREST_WORDS={
 'Temples':['temple','shrine','храм','собор'],
 'Saunas':['sauna','saunas','löyly','баня','саун'],
 'Spas':['spa','wellness','thermal','спа','термы'],
 'Food':['food','restaurants','gastronomy','cuisine','cafe','cafés','coffee','еда','ресторан','кухня'],
 'Museums':['museum','museums','музе','галере'],
 'Culture':['culture','cultural','history','sights','культур','достопримеч'],
 'History':['medieval','history','historic','castle','замки','истор'],
 'Architecture':['architecture','архитектура'],
 'Views':['viewpoint','view','scenic','обзор','виды'],
 'Outdoors':['parks','park','nature','greenery','природ','парк'],
 'Hiking':['hiking','hike','trekking','трек','поход','хайкинг'],
 'Beaches':['beach','sea','ocean','пляж','море'],
 'Nightlife':['nightlife','clubs','bars','вечеринки','клубы','бары'],
 'Shopping':['shopping','markets','магаз','шопинг'],
 'Music':['concert','live music','music','музык','концерт'],
 'Sports':['sports','sport','swimming','спорт','бассейн'],
}


def categorize_interests(interests: list[str]) -> list[str]:
    result=[]
    for interest in interests:
        val=interest.casefold().strip()
        for category, terms in INTEREST_WORDS.items():
            if val==category.casefold() or any(t in val for t in terms):
                if category not in result: result.append(category)
    return result


def _url(url: str, default: str) -> str:
    # Only public HTTPS destinations; block javascript/file and embedded credentials.
    from urllib.parse import urlsplit
    try:
        p=urlsplit(str(url))
        if p.scheme!='https' or not p.hostname or p.username or p.password: return default
        if p.hostname in ('localhost','127.0.0.1') or p.hostname.endswith('.local'): return default
        return url
    except ValueError: return default


def _point(name, category, url, source, details='', **more):
    return {'name':name[:135], 'category':category, 'url':url,
            'source':source, 'details':(details or '')[:190], **more}


async def _geocode(city: str, client: httpx.AsyncClient) -> tuple[float, float, str]:
    key=city.strip().casefold()
    c=GEO_CACHE.get(key)
    if c and c[0]>time.monotonic():return c[1]
    methods=(('Nominatim','https://nominatim.openstreetmap.org/search',
              {'q':city,'format':'jsonv2','limit':1,'addressdetails':1}),
             ('Photon','https://photon.komoot.io/api/',{'q':city,'limit':3}))
    for provider,endpoint,params in methods:
        try:
            r=await client.get(endpoint,params=params,timeout=5)
            r.raise_for_status();body=r.json()
            if provider=='Nominatim':
                p=next((x for x in body if x.get('type') in ('city','town','village','administrative','municipality','suburb') or x.get('addresstype') in ('city','town','village','municipality')),body[0])
                out=(float(p['lat']),float(p['lon']),p.get('address',{}).get('country',''))
            else:
                items=body['features'];p=next((x for x in items if x.get('properties',{}).get('osm_value') in ('city','town','village')),items[0])
                coords=p['geometry']['coordinates'];out=(float(coords[1]),float(coords[0]),p.get('properties',{}).get('country',''))
            GEO_CACHE[key]=(time.monotonic()+86400,out)
            return out
        except (httpx.HTTPError, IndexError, KeyError, ValueError, TypeError) as exc:
            logger.info('Geocoder %s unavailable: %s',provider,type(exc).__name__)
    # Independent fallback: city Wikipedia article's coordinates. Different backend.
    try:
        r=await client.get(WIKI,params={'action':'query','prop':'coordinates','titles':city,
            'format':'json','formatversion':2},timeout=5)
        r.raise_for_status()
        pages=r.json().get('query',{}).get('pages',[])
        coords=next((p['coordinates'][0] for p in pages if p.get('coordinates')),None)
        if coords:
            out=(float(coords['lat']),float(coords['lon']),'')
            GEO_CACHE[key]=(time.monotonic()+86400,out)
            return out
    except (httpx.HTTPError,ValueError,KeyError,TypeError,IndexError): pass
    raise LookupError('No supported geocoder could resolve the destination')


def _overpass_query(lat:float,lon:float,categories:list[str]) -> str:
    tags=[]
    for category in categories[:3]:tags.extend(TAXONOMY.get(category,[]))
    if not tags:tags=DEFAULT_TAGS
    # Preserve a small set of broad tourist highlights alongside specific intent.
    tags.extend([('tourism~','attraction|viewpoint'),('historic','castle')])
    selector=[]
    for key,value in dict.fromkeys(tags):
        if key.endswith('~'):
            selector.append(f'nwr(around:6500,{lat:.5f},{lon:.5f})["{key[:-1]}"~"{value}"]["name"];')
        else:selector.append(f'nwr(around:6500,{lat:.5f},{lon:.5f})["{key}"="{value}"]["name"];')
    return '[out:json][timeout:11];(' + ''.join(selector) + ');out center 100;'


def _classify_tags(tags:dict)->str:
    if tags.get('leisure')=='sauna' or re.search(r'\bsauna\b|löyly',tags.get('name',''),re.I): return 'Saunas'
    if tags.get('amenity')=='place_of_worship' or tags.get('building')=='temple':return 'Temples'
    if tags.get('tourism') in ('museum','gallery'):return 'Museums'
    if tags.get('tourism')=='viewpoint':return 'Views'
    if tags.get('natural')=='beach':return 'Beaches'
    if tags.get('leisure') in ('park','garden','nature_reserve'):return 'Outdoors'
    if tags.get('historic'):return 'History'
    if tags.get('amenity') in ('restaurant','cafe','marketplace'):return 'Food'
    if tags.get('amenity') in ('pub','bar','nightclub'):return 'Nightlife'
    return 'Culture'


async def _osm(lat:float,lon:float,interests:list[str],client:httpx.AsyncClient)->list[dict]:
    query=_overpass_query(lat,lon,categorize_interests(interests))
    last=None
    for server in OVERPASS:
        try:
            r=await client.post(server,data={'data':query},timeout=4.2)
            r.raise_for_status(); entries=r.json()['elements']
            result=[];seen=set()
            for el in entries:
                t=el.get('tags') or {};name=(t.get('name:en') or t.get('name') or '').strip()
                if len(name)<3 or name.casefold() in seen:continue
                seen.add(name.casefold())
                url=f'https://www.openstreetmap.org/{el["type"]}/{el["id"]}'
                website=_url(t.get('website') or t.get('contact:website') or '',url)
                result.append(_point(name,_classify_tags(t),website,'OpenStreetMap',
                                     t.get('description:en') or t.get('description') or '',osm_url=url))
            return result[:80]
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            last=exc;logger.info('Overpass %s unavailable: %s',server,type(exc).__name__)
    logger.warning('Overpass unavailable (%s)',type(last).__name__)
    return []


async def _wikimedia_geo(lat:float,lon:float,client:httpx.AsyncClient)->list[dict]:
    try:
        r=await client.get(WIKI,params={'action':'query','list':'geosearch','gscoord':f'{lat:.6f}|{lon:.6f}',
            'gsradius':9000,'gslimit':45,'format':'json'},timeout=7)
        r.raise_for_status();rows=r.json().get('query',{}).get('geosearch',[])
        return [_point(p['title'],'Culture','https://en.wikipedia.org/wiki/'+quote(p['title'].replace(' ','_')),
                       'Wikipedia · geolocated', f"{round(float(p.get('dist',0)))} m from city centre",distance_m=p.get('dist'))
                for p in rows if 'title' in p]
    except (httpx.HTTPError,ValueError,TypeError,KeyError) as exc:
        logger.info('Wikipedia geosearch unavailable: %s',type(exc).__name__)
        return []


async def _wikimedia_keyword(city:str, interests:list[str],client:httpx.AsyncClient)->list[dict]:
    # Key-free source-linked search supports niche intent even when the tag
    # taxonomy does not recognize it. Results are ARTICLES, not bookable venues.
    words=' '.join(i[:24] for i in interests[:2]) if interests else 'tourist attractions'
    words=re.sub(r'[^\w\sÀ-ÿ-]',' ',words)[:65]
    try:
        r=await client.get(WIKI,params={'action':'query','list':'search',
             'srsearch':f'{city} {words}', 'srnamespace':0,'srlimit':12,'format':'json'},timeout=7)
        r.raise_for_status()
        result=[]
        for p in r.json().get('query',{}).get('search',[]):
            title=p.get('title','')
            if not title or title.startswith(('List of','Category:')):continue
            result.append(_point(title,'Research','https://en.wikipedia.org/wiki/'+quote(title.replace(' ','_')),
                                'Wikipedia · article', 'Source-linked background; location/visitability not independently confirmed'))
        return result
    except (httpx.HTTPError,ValueError,TypeError,KeyError):return []


def _sort_places(places:list[dict],interests:list[str])->list[dict]:
    category_interest=set(categorize_interests(interests))
    keyword_tokens=set(re.findall(r'[\wÀ-ÿ]{4,}', ' '.join(interests).casefold()))
    def priority(p):
        name=p['name'].casefold()
        return ((p['category'] in category_interest)*6
                + min(2,sum(token in name for token in keyword_tokens))*3
                + (p['source']=='OpenStreetMap')*1.5
                + (p['source']=='Wikipedia · geolocated')*0.4)
    seen=set();out=[]
    for p in sorted(places,key=priority,reverse=True):
        key=re.sub(r'[^\w]','',p['name'].casefold())
        if key in seen:continue
        seen.add(key);out.append(p)
    return out[:24]


async def _load_live(city:str,interests:list[str])->dict:
    key=(city.casefold(),tuple(x.casefold() for x in interests[:5]))
    existing=CACHE.get(key)
    if existing and existing[0]>time.monotonic():return existing[1]
    async with httpx.AsyncClient(headers=HEADERS,follow_redirects=True) as client:
        keyword_task=asyncio.create_task(_wikimedia_keyword(city,interests,client))
        try:
            lat,lon,country=await _geocode(city,client)
            osm,wiki=await asyncio.gather(_osm(lat,lon,interests,client),
                                           _wikimedia_geo(lat,lon,client))
        except LookupError:
            country='';osm=[];wiki=[]
        keywords=await keyword_task
    locations=_sort_places(osm+wiki,interests)
    # Keyword pages only supplement confirmed coordinates; do not label them local venues.
    if not locations:
        locations=_sort_places(keywords,interests)
    result={'places':locations,'country':country,'source_type':
        ('openstreetmap_wikipedia' if osm and wiki else 'openstreetmap_live' if osm else
         'wikipedia_geosearch' if wiki else 'wikipedia_articles' if keywords else 'search_only'),
        'geo_located':bool(osm or wiki)}
    CACHE[key]=(time.monotonic()+3600,result)
    return result


def _search_links(city:str,interests:list[str])->list[dict]:
    terms=' '.join(interests[:2] or ['attractions'])
    query=quote(f'{city} {terms}')
    return [
        {'name':'OpenStreetMap','label':'Explore on map','url':'https://www.openstreetmap.org/search?query='+query},
        {'name':'Google Maps','label':'Find matching venues','url':'https://www.google.com/maps/search/?api=1&query='+query},
        {'name':'Wikipedia','label':'Read about this destination','url':'https://en.wikipedia.org/w/index.php?search='+query},
    ]


async def explore_trip(req:PlanRequest)->dict:
    live=await _load_live(req.destination,req.interests)
    places=live['places'];end=req.start_date+timedelta(days=req.days-1)
    days=[]
    for i in range(req.days):
        date=req.start_date+timedelta(days=i)
        # Spread diverse retrieved records across days without pretending opening-hours validation.
        n=max(1,req.days-1)
        picks=[p for j,p in enumerate(places[:min(18,2*n)]) if j%n==i][:2] if live['geo_located'] else []
        days.append({'number':i+1,'date':date.isoformat(),
                     'title':'Arrival & first impressions' if i==0 else ('Departure day' if i==req.days-1 else 'Explore your interests'),
                     'stops':[{'name':p['name'],'category':p['category'],'url':p['url']} for p in picks]})
    return {'status':'discovered' if places else 'search_links_only','mode':'live_discovery',
        'source_type':live['source_type'],'destination':req.destination,'country':live['country'],
        'origin':req.origin,'start_date':req.start_date.isoformat(), 'end_date':end.isoformat(),
        'days':req.days,'travelers':req.travelers,'budget':req.budget,'interests':req.interests,
        'last_checked':datetime.now(timezone.utc).isoformat(),'places':places,'count':len(places),
        'days_preview':days,'priced_venues':[], 'source_links':_search_links(req.destination,req.interests),
        'data_notice':'Live source records, not verified bookable inventory. Venue hours, location and admission must be confirmed independently.' if live['geo_located'] else
                      'Showing encyclopedia articles where available. No local venues or admission prices have been independently confirmed.',
        'budget_notice':f'€{req.budget:,} is your total ceiling. Flights, stays, ground transport and paid activities are NOT priced; this is discovery, not a confirmed all-in quote.',
        'providers':[
            {'name':'Google Flights','label':'Search flights','url':'https://www.google.com/travel/flights'},
            {'name':'Booking.com','label':'Search hotels','url':'https://www.booking.com/searchresults.html?ss='+quote(req.destination)},
            {'name':'Google Maps','label':'Explore places','url':'https://www.google.com/maps/search/?api=1&query='+quote(req.destination+' '+(' '.join(req.interests[:2]) or 'attractions'))},
        ],
        'attribution':'OpenStreetMap contributors (ODbL) and Wikipedia contributors (CC BY-SA). Links open original sources. Results can be incomplete.'}
