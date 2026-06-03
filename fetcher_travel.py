"""Hardcoded Barcelona travel recommendations for /travel."""

from __future__ import annotations

from typing import Any

UB_LAT = 41.3874
UB_LNG = 2.1686

TRAVEL_RECOMMENDATIONS_SEED: list[dict[str, Any]] = [
    {
        "id": "boqueria",
        "name": "La Boqueria Market",
        "name_es": "Mercado de La Boqueria",
        "lat": 41.3819,
        "lng": 2.1715,
        "address": "La Rambla, 91, Ciutat Vella",
        "description_es": "Mercado emblemático junto a la Rambla: fruta, pescado y tapas. Ideal para practicar español con los puestos.",
        "description_en": "Iconic market off La Rambla: fruit, fish, and tapas. Great for practicing Spanish with vendors.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=La+Boqueria+Barcelona",
        "travel_time_ub": "12 min a pie desde UB",
        "time": ["1-2h", "half"],
        "location": ["ub", "barcelona"],
        "distance": ["walk", "transit"],
        "mood": ["hungry", "cultural"],
    },
    {
        "id": "park-guell",
        "name": "Park Güell",
        "name_es": "Parque Güell",
        "lat": 41.4145,
        "lng": 2.1527,
        "address": "Carrer d'Olot, Gràcia",
        "description_es": "Parque modernista de Gaudí con vistas de la ciudad. Reserva entrada con antelación.",
        "description_en": "Gaudí's modernist park with city views. Book tickets in advance.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Park+Guell+Barcelona",
        "travel_time_ub": "25 min en metro (L3)",
        "time": ["half", "full"],
        "location": ["barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["adventure", "cultural"],
    },
    {
        "id": "barceloneta",
        "name": "Barceloneta Beach",
        "name_es": "Playa de la Barceloneta",
        "lat": 41.3784,
        "lng": 2.1925,
        "address": "Passeig Marítim, Barceloneta",
        "description_es": "Playa urbana para relajarse, pasear y comer en chiringuitos.",
        "description_en": "Urban beach to relax, stroll, and eat at beach bars.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Barceloneta+Beach",
        "travel_time_ub": "20 min en metro (L4)",
        "time": ["1-2h", "half", "full"],
        "location": ["beach", "barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["chill", "hungry"],
    },
    {
        "id": "mnac",
        "name": "MNAC",
        "name_es": "Museo Nacional de Arte de Cataluña",
        "lat": 41.3681,
        "lng": 2.1537,
        "address": "Parc de Montjuïc",
        "description_es": "Arte catalán y vistas desde la montaña de Montjuïc. Buen plan cultural de medio día.",
        "description_en": "Catalan art and views from Montjuïc hill. A solid half-day cultural plan.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=MNAC+Barcelona",
        "travel_time_ub": "18 min en metro + funicular",
        "time": ["half", "full"],
        "location": ["barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["cultural", "chill"],
    },
    {
        "id": "gracia-tapas",
        "name": "Gràcia neighborhood",
        "name_es": "Barrio de Gràcia",
        "lat": 41.4036,
        "lng": 2.1564,
        "address": "Gràcia, Barcelona",
        "description_es": "Plazas pequeñas, bares y ambiente local lejos del centro turístico.",
        "description_en": "Small squares, bars, and local vibe away from tourist center.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Gracia+Barcelona",
        "travel_time_ub": "15 min en metro (L3)",
        "time": ["1-2h", "half"],
        "location": ["ub", "barcelona"],
        "distance": ["walk", "transit"],
        "mood": ["hungry", "chill", "cultural"],
    },
    {
        "id": "sagrada-familia",
        "name": "Sagrada Família",
        "name_es": "La Sagrada Família",
        "lat": 41.4036,
        "lng": 2.1744,
        "address": "Carrer de Mallorca, 401",
        "description_es": "Basílica de Gaudí, símbolo de Barcelona. Compra entradas online para evitar colas.",
        "description_en": "Gaudí's basilica, symbol of Barcelona. Buy tickets online to skip lines.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Sagrada+Familia",
        "travel_time_ub": "12 min en metro (L2/L5)",
        "time": ["half", "full"],
        "location": ["ub", "barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["cultural", "adventure"],
    },
    {
        "id": "ciutadella",
        "name": "Parc de la Ciutadella",
        "name_es": "Parque de la Ciutadella",
        "lat": 41.3881,
        "lng": 2.1860,
        "address": "Passeig de Picasso, 21",
        "description_es": "Parque grande cerca del Born: paseo, picnic y el Arc de Triomf.",
        "description_en": "Large park near El Born: walks, picnic, and Arc de Triomf.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Parc+de+la+Ciutadella",
        "travel_time_ub": "15 min en metro o bici",
        "time": ["1-2h", "half"],
        "location": ["ub", "barcelona"],
        "distance": ["walk", "transit"],
        "mood": ["chill", "cultural"],
    },
    {
        "id": "montserrat",
        "name": "Montserrat",
        "name_es": "Montserrat",
        "lat": 41.5933,
        "lng": 1.8375,
        "address": "Monistrol de Montserrat, Catalonia",
        "description_es": "Monasterio en la montaña; excursion de día en tren desde Barcelona.",
        "description_en": "Mountain monastery; day trip by train from Barcelona.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Montserrat+Monastery",
        "travel_time_ub": "~1 h 30 en tren + cremallera",
        "time": ["full"],
        "location": ["spain"],
        "distance": ["anywhere"],
        "mood": ["adventure", "cultural"],
    },
    {
        "id": "sitges",
        "name": "Sitges",
        "name_es": "Sitges",
        "lat": 41.2370,
        "lng": 1.8055,
        "address": "Sitges, Barcelona province",
        "description_es": "Pueblo costero con playas y calles peatonales; tren Rodalies desde Sants.",
        "description_en": "Coastal town with beaches and pedestrian streets; Rodalies train from Sants.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Sitges",
        "travel_time_ub": "~40 min en tren desde Sants",
        "time": ["half", "full"],
        "location": ["spain", "beach"],
        "distance": ["anywhere"],
        "mood": ["chill", "adventure"],
    },
    {
        "id": "camp-nou-tour",
        "name": "Spotify Camp Nou tour",
        "name_es": "Tour del Camp Nou (FC Barcelona)",
        "lat": 41.3809,
        "lng": 2.1228,
        "address": "C. d'Aristides Maillol, Les Corts",
        "description_es": "Museo y estadio del Barça; imprescindible si te gusta el fútbol español.",
        "description_en": "Barça museum and stadium; essential if you love Spanish football.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Camp+Nou",
        "travel_time_ub": "20 min en metro (L3)",
        "time": ["half"],
        "location": ["barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["cultural", "adventure"],
    },
    {
        "id": "el-born",
        "name": "El Born cultural center",
        "name_es": "El Born CCultural",
        "lat": 41.3843,
        "lng": 2.1837,
        "address": "Plaça Comercial, 12",
        "description_es": "Ruinas arqueológicas y exposiciones sobre la historia de Barcelona.",
        "description_en": "Archaeological ruins and exhibits on Barcelona's history.",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=El+Born+Centre+Cultural",
        "travel_time_ub": "18 min en metro",
        "time": ["1-2h", "half"],
        "location": ["barcelona"],
        "distance": ["transit", "anywhere"],
        "mood": ["cultural"],
    },
]


def filter_travel_recommendations(
    time: str | None = None,
    location: str | None = None,
    distance: str | None = None,
    mood: str | None = None,
) -> list[dict[str, Any]]:
    """Return 3–5 recommendations matching filter tags."""
    scored: list[tuple[int, dict[str, Any]]] = []
    for rec in TRAVEL_RECOMMENDATIONS_SEED:
        score = 0
        if time and time in rec.get("time", []):
            score += 2
        elif not time:
            score += 1
        if location and location in rec.get("location", []):
            score += 2
        elif not location:
            score += 1
        if distance and distance in rec.get("distance", []):
            score += 2
        elif not distance:
            score += 1
        if mood and mood in rec.get("mood", []):
            score += 2
        elif not mood:
            score += 1
        if time and time not in rec.get("time", []):
            continue
        if location and location not in rec.get("location", []):
            continue
        if distance and distance not in rec.get("distance", []):
            continue
        if mood and mood not in rec.get("mood", []):
            continue
        scored.append((score, dict(rec)))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [r for _, r in scored[:5]]
    if len(results) < 3:
        results = [dict(r) for r in TRAVEL_RECOMMENDATIONS_SEED[:5]]
    return results[:5]
