"""Clearly synthetic travel inventory for an offline, reproducible MVP demo.

These numbers are NEVER marketed as bookable, live, or verified provider prices.
Replace these records via a licensed supplier adapter to enable real quotes.
"""

from __future__ import annotations

CITIES = {
    "Lisbon": {
        "country": "Portugal", "airport": "LIS", "emoji": "✦",
        "tagline": "Sunlit streets, ocean air, endless viewpoints.",
        "accent": "#D5E8FC", "accent2": "#A6C7F6", "theme": "Coastal city break",
        "train_hours": 9,
        "transit_pp": 18,
        "transport": [
            {"id": "bus", "name": "Overnight coach", "mode": "Coach", "pp": 58, "fees_pp": 0, "quality": 2, "detail": "Return · basic luggage included", "duration": "8h 30m"},
            {"id": "flight", "name": "Economy return flight", "mode": "Flight", "pp": 82, "fees_pp": 12, "quality": 7, "detail": "Return · cabin bag allowance", "duration": "1h 20m"},
            {"id": "train", "name": "Rail journey", "mode": "Train", "pp": 118, "fees_pp": 0, "quality": 6, "detail": "Return · standard class", "duration": "10h 15m"},
        ],
        "stays": [
            {"id": "hostel", "name": "Bright shared hostel", "night": 54, "fees": 22, "quality": 3, "detail": "Central neighborhood · private twin room"},
            {"id": "studio", "name": "Alfama city studio", "night": 72, "fees": 24, "quality": 8, "detail": "Walkable base · private kitchenette"},
            {"id": "hotel", "name": "Design boutique hotel", "night": 118, "fees": 20, "quality": 10, "detail": "Hotel comfort · central location"},
        ],
        "activities": [
            {"id": "alfama", "name": "Explore Alfama", "pp": 0, "score": 6, "duration": "2h", "category": "Culture"},
            {"id": "miradouro", "name": "Sunset at Miradouro", "pp": 0, "score": 7, "duration": "1h", "category": "Views"},
            {"id": "belem", "name": "Belém waterfront walk", "pp": 0, "score": 6, "duration": "2h", "category": "Culture"},
            {"id": "tram", "name": "Historic tram ride", "pp": 6, "score": 8, "duration": "1h", "category": "Local life"},
            {"id": "castle", "name": "São Jorge Castle", "pp": 16, "score": 9, "duration": "2h", "category": "History"},
            {"id": "cruise", "name": "Tagus sunset cruise", "pp": 28, "score": 8, "duration": "1h 30m", "category": "Outdoors"},
            {"id": "food", "name": "Portuguese tasting walk", "pp": 24, "score": 8, "duration": "2h", "category": "Food"},
        ],
        "moments": ["Alfama alleys", "Praça do Comércio", "Belém", "Bairro Alto", "Riverside sunset"],
    },
    "Porto": {
        "country": "Portugal", "airport": "OPO", "emoji": "◈", "tagline": "Riverside cafés and tiled facades.",
        "accent": "#E5DFF8", "accent2": "#B4A9F4", "theme": "Riverside weekend",
        "transit_pp": 14,
        "transport": [
            {"id": "bus", "name": "Overnight coach", "mode": "Coach", "pp": 64, "fees_pp": 0, "quality": 2, "detail": "Return · luggage included", "duration": "9h"},
            {"id": "flight", "name": "Economy return flight", "mode": "Flight", "pp": 97, "fees_pp": 14, "quality": 8, "detail": "Return · cabin bag", "duration": "1h 15m"},
            {"id": "train", "name": "Rail combination", "mode": "Train", "pp": 124, "fees_pp": 0, "quality": 6, "detail": "Return · standard", "duration": "10h"},
        ],
        "stays": [
            {"id": "hostel", "name": "Bolhão guesthouse", "night": 49, "fees": 18, "quality": 4, "detail": "Simple, central private room"},
            {"id": "studio", "name": "Ribeira loft", "night": 75, "fees": 20, "quality": 8, "detail": "Riverside apartment"},
            {"id": "hotel", "name": "Boutique river hotel", "night": 122, "fees": 25, "quality": 10, "detail": "Boutique river-view stay"},
        ],
        "activities": [
            {"id": "ribeira", "name": "Ribeira riverside walk", "pp": 0, "score": 8, "duration": "2h", "category": "Views"},
            {"id": "bridge", "name": "Dom Luís I Bridge", "pp": 0, "score": 7, "duration": "1h", "category": "Views"},
            {"id": "tiles", "name": "São Bento station", "pp": 0, "score": 6, "duration": "1h", "category": "Culture"},
            {"id": "book", "name": "Historic bookshop", "pp": 10, "score": 6, "duration": "1h", "category": "Culture"},
            {"id": "cruise", "name": "Six bridges cruise", "pp": 19, "score": 8, "duration": "1h", "category": "Outdoors"},
            {"id": "food", "name": "Porto food tasting", "pp": 26, "score": 8, "duration": "2h", "category": "Food"},
        ],
        "moments": ["Ribeira", "São Bento", "Dom Luís I Bridge", "Foz do Douro", "Porto sunsets"],
    },
    "Paris": {
        "country": "France", "airport": "CDG", "emoji": "✧", "tagline": "Iconic streets, art and early mornings.",
        "accent": "#FBE5DF", "accent2": "#F3AF98", "theme": "Art & city icons", "transit_pp": 32,
        "transport": [
            {"id": "bus", "name": "Long-distance coach", "mode": "Coach", "pp": 94, "fees_pp": 0, "quality": 1, "detail": "Return", "duration": "17h"},
            {"id": "flight", "name": "Economy return flight", "mode": "Flight", "pp": 146, "fees_pp": 16, "quality": 8, "detail": "Return · cabin bag", "duration": "2h 05m"},
            {"id": "train", "name": "Rail combination", "mode": "Train", "pp": 172, "fees_pp": 0, "quality": 6, "detail": "Return", "duration": "11h"},
        ],
        "stays": [
            {"id": "hostel", "name": "City guest room", "night": 78, "fees": 18, "quality": 3, "detail": "Metro-connected private room"},
            {"id": "studio", "name": "Montmartre apartment", "night": 109, "fees": 28, "quality": 8, "detail": "Private studio"},
            {"id": "hotel", "name": "Central boutique hotel", "night": 160, "fees": 22, "quality": 10, "detail": "Hotel comfort"},
        ],
        "activities": [
            {"id": "seine", "name": "Seine riverside walk", "pp": 0, "score": 8, "duration": "2h", "category": "Views"},
            {"id": "montmartre", "name": "Montmartre lanes", "pp": 0, "score": 7, "duration": "2h", "category": "Culture"},
            {"id": "louvre", "name": "Louvre museum", "pp": 22, "score": 9, "duration": "3h", "category": "Culture"},
            {"id": "tower", "name": "Eiffel Tower visit", "pp": 28, "score": 8, "duration": "2h", "category": "Views"},
            {"id": "cruise", "name": "Seine cruise", "pp": 18, "score": 7, "duration": "1h", "category": "Outdoors"},
        ],
        "moments": ["Montmartre", "Seine riverbanks", "Le Marais", "Latin Quarter", "Eiffel views"],
    },
    "Rome": {
        "country": "Italy", "airport": "FCO", "emoji": "◇", "tagline": "Ancient streets and long Italian evenings.",
        "accent": "#FBE8D2", "accent2": "#F2CB9A", "theme": "History & piazzas", "transit_pp": 22,
        "transport": [
            {"id": "bus", "name": "Budget coach", "mode": "Coach", "pp": 120, "fees_pp": 0, "quality": 1, "detail": "Return", "duration": "20h"},
            {"id": "flight", "name": "Economy return flight", "mode": "Flight", "pp": 112, "fees_pp": 20, "quality": 8, "detail": "Return · cabin bag", "duration": "2h 20m"},
            {"id": "train", "name": "Rail connections", "mode": "Train", "pp": 194, "fees_pp": 0, "quality": 5, "detail": "Return", "duration": "14h"},
        ],
        "stays": [
            {"id": "hostel", "name": "Trastevere guest room", "night": 61, "fees": 20, "quality": 4, "detail": "Private guest room"},
            {"id": "studio", "name": "Centro Storico studio", "night": 91, "fees": 26, "quality": 8, "detail": "Walkable apartment"},
            {"id": "hotel", "name": "Design hotel near Pantheon", "night": 145, "fees": 23, "quality": 10, "detail": "Central boutique stay"},
        ],
        "activities": [
            {"id": "piazza", "name": "Piazza Navona", "pp": 0, "score": 8, "duration": "1h", "category": "Culture"},
            {"id": "fountain", "name": "Trevi Fountain", "pp": 0, "score": 7, "duration": "1h", "category": "Views"},
            {"id": "trastevere", "name": "Trastevere stroll", "pp": 0, "score": 7, "duration": "2h", "category": "Local life"},
            {"id": "colosseum", "name": "Colosseum visit", "pp": 22, "score": 9, "duration": "2h", "category": "History"},
            {"id": "vatican", "name": "Vatican museums", "pp": 25, "score": 9, "duration": "3h", "category": "History"},
        ],
        "moments": ["Trastevere", "Pantheon", "Piazza Navona", "Roman Forum", "Trevi at night"],
    },
    "Prague": {
        "country": "Czechia", "airport": "PRG", "emoji": "✺", "tagline": "Historic rooftops and walkable lanes.",
        "accent": "#DAF0E7", "accent2": "#A2DBCA", "theme": "Old-town discoveries", "transit_pp": 18,
        "transport": [
            {"id": "bus", "name": "Budget coach", "mode": "Coach", "pp": 106, "fees_pp": 0, "quality": 1, "detail": "Return", "duration": "23h"},
            {"id": "flight", "name": "Economy return flight", "mode": "Flight", "pp": 144, "fees_pp": 16, "quality": 8, "detail": "Return · cabin bag", "duration": "2h 40m"},
            {"id": "train", "name": "Rail connections", "mode": "Train", "pp": 180, "fees_pp": 0, "quality": 5, "detail": "Return", "duration": "18h"},
        ],
        "stays": [
            {"id": "hostel", "name": "Old Town guest room", "night": 52, "fees": 18, "quality": 4, "detail": "Walkable private room"},
            {"id": "studio", "name": "Vinohrady studio", "night": 76, "fees": 22, "quality": 8, "detail": "Apartment near transit"},
            {"id": "hotel", "name": "Riverside boutique hotel", "night": 121, "fees": 20, "quality": 10, "detail": "Central design hotel"},
        ],
        "activities": [
            {"id": "bridge", "name": "Charles Bridge at dawn", "pp": 0, "score": 8, "duration": "1h", "category": "Views"},
            {"id": "town", "name": "Old Town Square", "pp": 0, "score": 7, "duration": "2h", "category": "Culture"},
            {"id": "park", "name": "Letná park viewpoint", "pp": 0, "score": 6, "duration": "1h", "category": "Outdoors"},
            {"id": "castle", "name": "Prague Castle tour", "pp": 18, "score": 9, "duration": "2h", "category": "History"},
            {"id": "cruise", "name": "Vltava river cruise", "pp": 23, "score": 7, "duration": "1h", "category": "Outdoors"},
        ],
        "moments": ["Charles Bridge", "Old Town", "Prague Castle", "Letná", "Vltava River"],
    },
}
