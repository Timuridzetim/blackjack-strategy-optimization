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


def test_api():
    r=client.post('/api/plan',json={'origin':'Madrid','destination':'Lisbon','days':5,'travelers':2,'budget':700,'start_date':'2026-12-08'})
    assert r.status_code==200
    assert r.json()['alternatives'][0]['total']<=700


def test_arbitrary_destination_does_not_invent_prices():
    r=client.post('/api/plan',json={'destination':'Moon'})
    assert r.status_code==200
    data=r.json()
    assert data['mode']=='live_discovery'
    assert 'budget_notice' in data
    assert 'alternatives' not in data


def test_prevent_html_injection_in_origin():
    r=client.post('/api/plan',json={'origin':'<script>alert(1)</script>'})
    assert r.status_code==200  # HTML escaping happens in front end; API returns structured JSON


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

def test_helsinki_real_venue_fallback_without_flight_pricing():
    from app.discovery import explore_trip
    import asyncio
    data=asyncio.run(explore_trip(PlanRequest(destination='Helsinki',interests=['Saunas'],budget=5000,travelers=4)))
    assert data['mode']=='live_discovery' and data['budget']==5000
    assert any('Löyly' in p['name'] for p in data['places'])
    assert 'NOT quoted' in data['budget_notice']
    assert data['count']>=4
