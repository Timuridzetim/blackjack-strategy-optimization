from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.engine import PlanRequest,plan_trip,parse_message

client=TestClient(app)

def test_health():
    result=client.get('/api/health')
    assert result.status_code==200 and result.json()['ok']


def test_budget_always_hard_cap():
    for city in ('Lisbon','Porto','Paris','Rome','Prague'):
        for budget in (200,350,500,700,900,1200,2000):
            r=plan_trip(PlanRequest(destination=city,budget=budget,travelers=2,days=5))
            for option in r['alternatives']:
                assert option['total']<=budget, (city,budget,option)
                assert sum(x['amount'] for x in option['breakdown'])==option['total']
                assert len(option['days'])==5
                assert option['remaining']==budget-option['total']


def test_lisbon_baseline_feasible():
    r=plan_trip(PlanRequest(origin='Madrid',destination='Lisbon',travelers=2,days=5,budget=700))
    assert r['status']=='ready'
    assert len(r['alternatives'])>=2
    assert r['source_type']=='synthetic_catalog'
    assert 'not live' in r['data_notice'].lower()


def test_low_budget_not_faked():
    r=plan_trip(PlanRequest(destination='Paris',days=9,travelers=6,budget=250))
    assert r['status']=='over_budget'
    assert r['alternatives']==[]
    assert r['estimated_shortfall']>0


def test_parser():
    d=parse_message('Plan 5 days from Madrid to Lisbon for 2 people under €700')
    assert d['destination']=='Lisbon' and d['origin']=='Madrid'
    assert d['days']==5 and d['travelers']==2 and d['budget']==700


def test_api(monkeypatch):
    import app.discovery as discovery
    async def fake(city, interests):
        return {'places':[{'name':'Sample Museum','category':'Museums','url':'https://en.wikipedia.org/wiki/Museum','source':'Wikipedia · geolocated','details':'source record'}],
                'country':'Portugal','source_type':'wikipedia_geosearch','geo_located':True}
    monkeypatch.setattr(discovery,'_load_live',fake)
    r=client.post('/api/plan',json={'origin':'Madrid','destination':'Lisbon','days':5,'travelers':2,'budget':700,'start_date':'2026-12-08'})
    assert r.status_code==200
    assert r.json()['mode']=='live_discovery'
    assert r.json()['places'][0]['name']=='Sample Museum'
    assert 'alternatives' not in r.json()


def test_arbitrary_destination_does_not_invent_prices(monkeypatch):
    import app.discovery as discovery
    async def fake(city, interests):
        return {'places':[], 'country':'', 'source_type':'search_only','geo_located':False}
    monkeypatch.setattr(discovery,'_load_live',fake)
    r=client.post('/api/plan',json={'destination':'Moon'})
    assert r.status_code==200
    data=r.json()
    assert data['mode']=='live_discovery'
    assert 'budget_notice' in data and 'alternatives' not in data
    assert data['count']==0 and len(data['source_links'])>=2


def test_prevent_html_injection_in_origin():
    # Structured request accepts origin as text; front-end applies esc() to every
    # user-supplied and remotely sourced visible value.
    assert PlanRequest(origin='<script>alert(1)</script>').origin.startswith('<script>')
    js=open(__import__('pathlib').Path(__file__).parents[1]/'app/static/app.js',encoding='utf8').read()
    assert "const esc =" in js and 'esc(d.origin)' in js


def test_preference_changes_initial_choice():
    base={'destination':'Lisbon','budget':900,'travelers':2,'days':5}
    saving=plan_trip(PlanRequest(**base,preference='save'))
    comfort=plan_trip(PlanRequest(**base,preference='comfort'))
    assert saving['alternatives'][0]['label']=='Lowest cost'
    assert comfort['alternatives'][0]['label']=='More comfort'
    assert saving['alternatives'][0]['total']<=comfort['alternatives'][0]['total']


def test_helsinki_free_text_parsing():
    from app.intent import fallback_parse
    d=fallback_parse('Helsinki for 4 people, 5K euros total, 5 days, saunas', {'destination':'Lisbon','travelers':2,'budget':700})
    assert d['destination']=='Helsinki' and d['travelers']==4 and d['budget']==5000 and d['days']==5
    assert 'Saunas' in d['interests']

def test_russian_guide_parsing():
    from app.intent import fallback_parse
    d=fallback_parse('В Хельсинки на 5 дней, 4 человека, 5000 евро, сауны')
    assert d['destination']=='Helsinki' and d['travelers']==4 and d['budget']==5000 and d['days']==5

def test_generic_city_discovery_does_not_use_preloaded_places(monkeypatch):
    import asyncio
    import app.discovery as discovery
    async def search(city,interests):
        assert city=='Ulaanbaatar'
        return {'places':[{'name':'Named real park','category':'Outdoors','url':'https://www.openstreetmap.org/node/1',
                 'source':'OpenStreetMap','details':''}],
                'country':'Mongolia','source_type':'openstreetmap_live','geo_located':True}
    monkeypatch.setattr(discovery,'_load_live',search)
    result=asyncio.run(discovery.explore_trip(PlanRequest(destination='Ulaanbaatar',interests=['Hiking'])))
    assert result['count']==1
    assert result['source_type']=='openstreetmap_live'
    assert result['places'][0]['source']=='OpenStreetMap'
    assert 'NOT priced' in result['budget_notice']


def test_generic_cities_and_interests():
    from app.intent import fallback_parse
    cases=[
      ('Tallinn for 2 people, €700 total, 4 days, medieval castles and sea','Tallinn',700,2,4),
      ('Helsinki, 4 people, €5,000 total, 5 days. We want saunas and local food','Helsinki',5000,4,5),
      ('Kyoto, 3 people, €2,000 total. We want temples and food','Kyoto',2000,3,None),
      ('I want to go to Ulaanbaatar for 3 people under €1000, love hiking','Ulaanbaatar',1000,3,None),
      ('Travel to San Sebastian for 4 people, wine tours','San Sebastian',None,4,None),
      ('I want to visit Marrakech for 3 people under 5k euros','Marrakech',5000,3,None),
    ]
    for prompt,city,budget,people,days in cases:
        p=fallback_parse(prompt,{'destination':'Lisbon','budget':700,'travelers':2})
        assert p['destination']==city,(prompt,p)
        if budget:assert p['budget']==budget,(prompt,p)
        assert p['travelers']==people,(prompt,p)
        if days:assert p['days']==days,(prompt,p)
    assert 'wine tours' in fallback_parse('Travel to San Sebastian for 4 people, wine tours')['interests']
    assert 'Temples' in fallback_parse('Kyoto for 4 people. We want temples')['interests']


def test_osm_query_uses_generic_interest_mapping():
    import app.discovery as d
    q=d._overpass_query(35.6762,139.6503,['Temples'])
    assert 'place_of_worship' in q
    assert '35.67620' in q
    assert 'Tallinn' not in q and 'Helsinki' not in q
    q2=d._overpass_query(-12.0464,-77.0428,['Food'])
    assert 'restaurant' in q2 and 'Lima' not in q2


def test_dynamic_http_source_fallback(monkeypatch):
    # Simulate: Nominatim denied, Photon succeeds, Overpass down,
    # Wikipedia geosearch supplies two real geolocated encyclopedia entries.
    import app.discovery as d
    import asyncio, httpx
    d.CACHE.clear();d.GEO_CACHE.clear()
    def handler(request):
        url=str(request.url)
        if 'nominatim' in url or 'overpass' in url:
            return httpx.Response(503,json={'error':'busy'})
        if 'photon.komoot.io' in url:
            return httpx.Response(200,json={'features':[{'geometry':{'coordinates':[139.69,35.69]},
                        'properties':{'country':'Japan','osm_value':'city'}}]})
        if 'en.wikipedia.org' in url and 'geosearch' in url:
            return httpx.Response(200,json={'query':{'geosearch':[{'title':'Tokyo Tower','dist':890},
                                               {'title':'Ueno Park','dist':1700}]}})
        return httpx.Response(200,json={'query':{'search':[]}})
    class FakeClient(httpx.AsyncClient):
        def __init__(self,*args,**kwargs):
            kwargs['transport']=httpx.MockTransport(handler)
            super().__init__(*args,**kwargs)
    monkeypatch.setattr(d.httpx,'AsyncClient',FakeClient)
    result=asyncio.run(d._load_live('Tokyo',['Views']))
    assert result['source_type']=='wikipedia_geosearch'
    assert any(p['name']=='Tokyo Tower' for p in result['places'])
    assert result['country']=='Japan'
    assert all(p['url'].startswith('https://en.wikipedia.org') for p in result['places'])


def test_search_links_only_mode_is_honest(monkeypatch):
    import asyncio, app.discovery as d
    async def nothing(city,interests):
        return {'places':[],'country':'','source_type':'search_only','geo_located':False}
    monkeypatch.setattr(d,'_load_live',nothing)
    r=asyncio.run(d.explore_trip(PlanRequest(destination='Pucón',budget=2000)))
    assert r['status']=='search_links_only' and r['count']==0
    assert any('Puc' in s['url'] for s in r['source_links'])
    assert not r['priced_venues']


def test_rejects_unsafe_media_url():
    import app.discovery as d
    assert d._url('javascript:alert(1)','https://www.openstreetmap.org')=='https://www.openstreetmap.org'
    assert d._url('http://127.0.0.1/x','https://www.openstreetmap.org')=='https://www.openstreetmap.org'
