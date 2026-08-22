"""Bundled airport reference data, typeahead lookup, and city-name resolution.

Coordinates are approximate to a few kilometres. They exist to give the fare
simulator a plausible distance term, not to navigate an aircraft.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, asdict

# iata, airport name, city, country, latitude, longitude, is_primary_for_city
_ROWS: tuple[tuple[str, str, str, str, float, float, bool], ...] = (
    # ---- United States ----
    ("ATL", "Hartsfield-Jackson Atlanta International", "Atlanta", "United States", 33.64, -84.43, True),
    ("AUS", "Austin-Bergstrom International", "Austin", "United States", 30.20, -97.67, True),
    ("BNA", "Nashville International", "Nashville", "United States", 36.13, -86.67, True),
    ("BOS", "Logan International", "Boston", "United States", 42.36, -71.01, True),
    ("BWI", "Baltimore/Washington International", "Baltimore", "United States", 39.18, -76.67, True),
    ("CLE", "Cleveland Hopkins International", "Cleveland", "United States", 41.41, -81.85, True),
    ("CLT", "Charlotte Douglas International", "Charlotte", "United States", 35.21, -80.94, True),
    ("DCA", "Ronald Reagan Washington National", "Washington", "United States", 38.85, -77.04, True),
    ("DEN", "Denver International", "Denver", "United States", 39.86, -104.67, True),
    ("DFW", "Dallas/Fort Worth International", "Dallas", "United States", 32.90, -97.04, True),
    ("DTW", "Detroit Metropolitan Wayne County", "Detroit", "United States", 42.21, -83.35, True),
    ("EWR", "Newark Liberty International", "New York", "United States", 40.69, -74.17, False),
    ("FLL", "Fort Lauderdale-Hollywood International", "Fort Lauderdale", "United States", 26.07, -80.15, True),
    ("HNL", "Daniel K. Inouye International", "Honolulu", "United States", 21.32, -157.92, True),
    ("IAD", "Washington Dulles International", "Washington", "United States", 38.95, -77.46, False),
    ("IAH", "George Bush Intercontinental", "Houston", "United States", 29.99, -95.34, True),
    ("JFK", "John F. Kennedy International", "New York", "United States", 40.64, -73.78, True),
    ("LAS", "Harry Reid International", "Las Vegas", "United States", 36.08, -115.15, True),
    ("LAX", "Los Angeles International", "Los Angeles", "United States", 33.94, -118.41, True),
    ("LGA", "LaGuardia", "New York", "United States", 40.78, -73.87, False),
    ("MCI", "Kansas City International", "Kansas City", "United States", 39.30, -94.71, True),
    ("MCO", "Orlando International", "Orlando", "United States", 28.43, -81.31, True),
    ("MDW", "Chicago Midway International", "Chicago", "United States", 41.79, -87.75, False),
    ("MIA", "Miami International", "Miami", "United States", 25.80, -80.29, True),
    ("MSP", "Minneapolis-Saint Paul International", "Minneapolis", "United States", 44.88, -93.22, True),
    ("MSY", "Louis Armstrong New Orleans International", "New Orleans", "United States", 29.99, -90.26, True),
    ("OAK", "Oakland International", "Oakland", "United States", 37.72, -122.22, True),
    ("ORD", "O'Hare International", "Chicago", "United States", 41.98, -87.90, True),
    ("PDX", "Portland International", "Portland", "United States", 45.59, -122.60, True),
    ("PHL", "Philadelphia International", "Philadelphia", "United States", 39.87, -75.24, True),
    ("PHX", "Phoenix Sky Harbor International", "Phoenix", "United States", 33.43, -112.01, True),
    ("PIT", "Pittsburgh International", "Pittsburgh", "United States", 40.49, -80.23, True),
    ("RDU", "Raleigh-Durham International", "Raleigh", "United States", 35.88, -78.79, True),
    ("SAN", "San Diego International", "San Diego", "United States", 32.73, -117.19, True),
    ("SAT", "San Antonio International", "San Antonio", "United States", 29.53, -98.47, True),
    ("SEA", "Seattle-Tacoma International", "Seattle", "United States", 47.45, -122.31, True),
    ("SFO", "San Francisco International", "San Francisco", "United States", 37.62, -122.38, True),
    ("SJC", "Norman Y. Mineta San Jose International", "San Jose", "United States", 37.36, -121.93, True),
    ("SLC", "Salt Lake City International", "Salt Lake City", "United States", 40.79, -111.98, True),
    ("SMF", "Sacramento International", "Sacramento", "United States", 38.70, -121.59, True),
    ("STL", "St. Louis Lambert International", "St. Louis", "United States", 38.75, -90.37, True),
    ("TPA", "Tampa International", "Tampa", "United States", 27.98, -82.53, True),
    # ---- Canada ----
    ("YUL", "Montreal-Trudeau International", "Montreal", "Canada", 45.47, -73.74, True),
    ("YVR", "Vancouver International", "Vancouver", "Canada", 49.19, -123.18, True),
    ("YYC", "Calgary International", "Calgary", "Canada", 51.13, -114.01, True),
    ("YYZ", "Toronto Pearson International", "Toronto", "Canada", 43.68, -79.63, True),
    # ---- Latin America ----
    ("BOG", "El Dorado International", "Bogota", "Colombia", 4.70, -74.15, True),
    ("CUN", "Cancun International", "Cancun", "Mexico", 21.04, -86.87, True),
    ("EZE", "Ministro Pistarini International", "Buenos Aires", "Argentina", -34.82, -58.54, True),
    ("GIG", "Rio de Janeiro/Galeao International", "Rio de Janeiro", "Brazil", -22.81, -43.25, True),
    ("GRU", "Sao Paulo/Guarulhos International", "Sao Paulo", "Brazil", -23.43, -46.47, True),
    ("LIM", "Jorge Chavez International", "Lima", "Peru", -12.02, -77.11, True),
    ("MEX", "Mexico City International", "Mexico City", "Mexico", 19.44, -99.07, True),
    ("MVD", "Carrasco International", "Montevideo", "Uruguay", -34.84, -56.03, True),
    ("PTY", "Tocumen International", "Panama City", "Panama", 9.07, -79.38, True),
    ("SCL", "Arturo Merino Benitez International", "Santiago", "Chile", -33.39, -70.79, True),
    ("SJO", "Juan Santamaria International", "San Jose", "Costa Rica", 9.99, -84.21, False),
    ("UIO", "Mariscal Sucre International", "Quito", "Ecuador", -0.13, -78.36, True),
    # ---- Europe ----
    ("AMS", "Amsterdam Schiphol", "Amsterdam", "Netherlands", 52.31, 4.76, True),
    ("ARN", "Stockholm Arlanda", "Stockholm", "Sweden", 59.65, 17.92, True),
    ("ATH", "Athens International", "Athens", "Greece", 37.94, 23.95, True),
    ("BCN", "Josep Tarradellas Barcelona-El Prat", "Barcelona", "Spain", 41.30, 2.08, True),
    ("BER", "Berlin Brandenburg", "Berlin", "Germany", 52.36, 13.50, True),
    ("BRU", "Brussels", "Brussels", "Belgium", 50.90, 4.48, True),
    ("BUD", "Budapest Ferenc Liszt International", "Budapest", "Hungary", 47.44, 19.26, True),
    ("CDG", "Paris Charles de Gaulle", "Paris", "France", 49.01, 2.55, True),
    ("CPH", "Copenhagen", "Copenhagen", "Denmark", 55.62, 12.66, True),
    ("DUB", "Dublin", "Dublin", "Ireland", 53.43, -6.25, True),
    ("DUS", "Dusseldorf", "Dusseldorf", "Germany", 51.29, 6.77, True),
    ("EDI", "Edinburgh", "Edinburgh", "United Kingdom", 55.95, -3.37, True),
    ("FCO", "Rome Fiumicino", "Rome", "Italy", 41.80, 12.25, True),
    ("FRA", "Frankfurt", "Frankfurt", "Germany", 50.04, 8.56, True),
    ("GVA", "Geneva", "Geneva", "Switzerland", 46.24, 6.11, True),
    ("HAM", "Hamburg", "Hamburg", "Germany", 53.63, 10.01, True),
    ("HEL", "Helsinki-Vantaa", "Helsinki", "Finland", 60.32, 24.96, True),
    ("KEF", "Keflavik International", "Reykjavik", "Iceland", 63.99, -22.62, True),
    ("LCY", "London City", "London", "United Kingdom", 51.51, 0.06, False),
    ("LGW", "London Gatwick", "London", "United Kingdom", 51.15, -0.19, False),
    ("LHR", "London Heathrow", "London", "United Kingdom", 51.47, -0.45, True),
    ("LIS", "Humberto Delgado (Lisbon)", "Lisbon", "Portugal", 38.77, -9.13, True),
    ("LYS", "Lyon-Saint Exupery", "Lyon", "France", 45.73, 5.08, True),
    ("MAD", "Adolfo Suarez Madrid-Barajas", "Madrid", "Spain", 40.47, -3.56, True),
    ("MAN", "Manchester", "Manchester", "United Kingdom", 53.35, -2.28, True),
    ("MRS", "Marseille Provence", "Marseille", "France", 43.44, 5.21, True),
    ("MUC", "Munich", "Munich", "Germany", 48.35, 11.79, True),
    ("MXP", "Milan Malpensa", "Milan", "Italy", 45.63, 8.72, True),
    ("NCE", "Nice Cote d'Azur", "Nice", "France", 43.66, 7.21, True),
    ("OPO", "Francisco Sa Carneiro (Porto)", "Porto", "Portugal", 41.24, -8.68, True),
    ("OSL", "Oslo Gardermoen", "Oslo", "Norway", 60.19, 11.10, True),
    ("OTP", "Henri Coanda International", "Bucharest", "Romania", 44.57, 26.10, True),
    ("PMI", "Palma de Mallorca", "Palma", "Spain", 39.55, 2.74, True),
    ("PRG", "Vaclav Havel Prague", "Prague", "Czech Republic", 50.10, 14.26, True),
    ("STN", "London Stansted", "London", "United Kingdom", 51.89, 0.24, False),
    ("SVQ", "Seville", "Seville", "Spain", 37.42, -5.89, True),
    ("TLS", "Toulouse-Blagnac", "Toulouse", "France", 43.63, 1.37, True),
    ("VCE", "Venice Marco Polo", "Venice", "Italy", 45.51, 12.35, True),
    ("VIE", "Vienna International", "Vienna", "Austria", 48.11, 16.57, True),
    ("VLC", "Valencia", "Valencia", "Spain", 39.49, -0.48, True),
    ("WAW", "Warsaw Chopin", "Warsaw", "Poland", 52.17, 20.97, True),
    ("ZRH", "Zurich", "Zurich", "Switzerland", 47.46, 8.55, True),
    # ---- Middle East & Africa ----
    ("ACC", "Kotoka International", "Accra", "Ghana", 5.61, -0.17, True),
    ("ADD", "Addis Ababa Bole International", "Addis Ababa", "Ethiopia", 8.98, 38.80, True),
    ("AMM", "Queen Alia International", "Amman", "Jordan", 31.72, 35.99, True),
    ("AUH", "Zayed International", "Abu Dhabi", "United Arab Emirates", 24.43, 54.65, True),
    ("CAI", "Cairo International", "Cairo", "Egypt", 30.11, 31.41, True),
    ("CMN", "Mohammed V International", "Casablanca", "Morocco", 33.37, -7.59, True),
    ("CPT", "Cape Town International", "Cape Town", "South Africa", -33.97, 18.60, True),
    ("DOH", "Hamad International", "Doha", "Qatar", 25.27, 51.61, True),
    ("DXB", "Dubai International", "Dubai", "United Arab Emirates", 25.25, 55.36, True),
    ("IST", "Istanbul", "Istanbul", "Turkey", 41.26, 28.74, True),
    ("JED", "King Abdulaziz International", "Jeddah", "Saudi Arabia", 21.68, 39.16, True),
    ("JNB", "O. R. Tambo International", "Johannesburg", "South Africa", -26.14, 28.25, True),
    ("LOS", "Murtala Muhammed International", "Lagos", "Nigeria", 6.58, 3.32, True),
    ("NBO", "Jomo Kenyatta International", "Nairobi", "Kenya", -1.32, 36.93, True),
    ("RUH", "King Khalid International", "Riyadh", "Saudi Arabia", 24.96, 46.70, True),
    ("TLV", "Ben Gurion", "Tel Aviv", "Israel", 32.01, 34.89, True),
    ("TUN", "Tunis-Carthage", "Tunis", "Tunisia", 36.85, 10.23, True),
    # ---- Asia ----
    ("BKK", "Suvarnabhumi", "Bangkok", "Thailand", 13.69, 100.75, True),
    ("BLR", "Kempegowda International", "Bengaluru", "India", 13.20, 77.71, True),
    ("BOM", "Chhatrapati Shivaji Maharaj International", "Mumbai", "India", 19.09, 72.87, True),
    ("CAN", "Guangzhou Baiyun International", "Guangzhou", "China", 23.39, 113.30, True),
    ("CCU", "Netaji Subhas Chandra Bose International", "Kolkata", "India", 22.65, 88.45, True),
    ("CGK", "Soekarno-Hatta International", "Jakarta", "Indonesia", -6.13, 106.66, True),
    ("CMB", "Bandaranaike International", "Colombo", "Sri Lanka", 7.18, 79.88, True),
    ("DAC", "Hazrat Shahjalal International", "Dhaka", "Bangladesh", 23.84, 90.40, True),
    ("DEL", "Indira Gandhi International", "Delhi", "India", 28.56, 77.10, True),
    ("DPS", "Ngurah Rai International", "Denpasar", "Indonesia", -8.75, 115.17, True),
    ("HAN", "Noi Bai International", "Hanoi", "Vietnam", 21.22, 105.81, True),
    ("HKG", "Hong Kong International", "Hong Kong", "Hong Kong", 22.31, 113.91, True),
    ("HND", "Tokyo Haneda", "Tokyo", "Japan", 35.55, 139.78, True),
    ("HYD", "Rajiv Gandhi International", "Hyderabad", "India", 17.24, 78.43, True),
    ("ICN", "Incheon International", "Seoul", "South Korea", 37.46, 126.44, True),
    ("KIX", "Kansai International", "Osaka", "Japan", 34.43, 135.24, True),
    ("KTM", "Tribhuvan International", "Kathmandu", "Nepal", 27.70, 85.36, True),
    ("KUL", "Kuala Lumpur International", "Kuala Lumpur", "Malaysia", 2.75, 101.71, True),
    ("MAA", "Chennai International", "Chennai", "India", 12.99, 80.17, True),
    ("MNL", "Ninoy Aquino International", "Manila", "Philippines", 14.51, 121.02, True),
    ("NRT", "Tokyo Narita", "Tokyo", "Japan", 35.76, 140.39, False),
    ("PEK", "Beijing Capital International", "Beijing", "China", 40.08, 116.58, True),
    ("PVG", "Shanghai Pudong International", "Shanghai", "China", 31.14, 121.81, True),
    ("SGN", "Tan Son Nhat International", "Ho Chi Minh City", "Vietnam", 10.82, 106.66, True),
    ("SIN", "Singapore Changi", "Singapore", "Singapore", 1.36, 103.99, True),
    ("TPE", "Taiwan Taoyuan International", "Taipei", "Taiwan", 25.08, 121.23, True),
    # ---- Oceania ----
    ("AKL", "Auckland", "Auckland", "New Zealand", -37.01, 174.79, True),
    ("BNE", "Brisbane", "Brisbane", "Australia", -27.38, 153.12, True),
    ("CHC", "Christchurch", "Christchurch", "New Zealand", -43.49, 172.53, True),
    ("MEL", "Melbourne", "Melbourne", "Australia", -37.67, 144.84, True),
    ("NAN", "Nadi International", "Nadi", "Fiji", -17.76, 177.44, True),
    ("PER", "Perth", "Perth", "Australia", -31.94, 115.97, True),
    ("PPT", "Faa'a International", "Papeete", "French Polynesia", -17.56, -149.61, True),
    ("SYD", "Sydney Kingsford Smith", "Sydney", "Australia", -33.95, 151.18, True),
    ("WLG", "Wellington", "Wellington", "New Zealand", -41.33, 174.81, True),
)


@dataclass(frozen=True)
class Airport:
    iata: str
    name: str
    city: str
    country: str
    lat: float
    lon: float
    primary: bool

    @property
    def label(self) -> str:
        return f"{self.city} ({self.iata})"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["label"] = self.label
        return data


AIRPORTS: dict[str, Airport] = {
    row[0]: Airport(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in _ROWS
}

# Extra spoken names that are not the canonical city string. Deliberately does
# NOT alias "Roma" to Rome: in this product that word is the agent's name.
_CITY_ALIASES: dict[str, str] = {
    "nyc": "New York",
    "new york city": "New York",
    "manhattan": "New York",
    "la": "Los Angeles",
    "los angeles ca": "Los Angeles",
    "sf": "San Francisco",
    "san fran": "San Francisco",
    "bay area": "San Francisco",
    "silicon valley": "San Jose",
    "d.c.": "Washington",
    "dc": "Washington",
    "washington dc": "Washington",
    "the big apple": "New York",
    "bombay": "Mumbai",
    "bangalore": "Bengaluru",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "saigon": "Ho Chi Minh City",
    "bali": "Denpasar",
    "tahiti": "Papeete",
    "holland": "Amsterdam",
    "the netherlands": "Amsterdam",
    "england": "London",
    "great britain": "London",
    "uk": "London",
    "japan": "Tokyo",
    "south africa": "Johannesburg",
    "sthlm": "Stockholm",
    "koln": "Dusseldorf",
    "cologne": "Dusseldorf",
    "florence": "Rome",
    "tel-aviv": "Tel Aviv",
    "hawaii": "Honolulu",
    "oahu": "Honolulu",
    "mexico": "Mexico City",
    "sao paolo": "Sao Paulo",
    "vegas": "Las Vegas",
    "nola": "New Orleans",
    "philly": "Philadelphia",
    "chi town": "Chicago",
    "beantown": "Boston",
}


def _fold(text: str) -> str:
    """Lowercase, strip accents and punctuation, squeeze whitespace."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", stripped.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


_CITY_INDEX: dict[str, list[str]] = {}
for _code, _airport in AIRPORTS.items():
    _CITY_INDEX.setdefault(_fold(_airport.city), []).append(_code)
for _alias, _city in _CITY_ALIASES.items():
    codes = _CITY_INDEX.get(_fold(_city))
    if codes:
        _CITY_INDEX.setdefault(_fold(_alias), []).extend(codes)


def _primary_of(codes: list[str]) -> str:
    for code in codes:
        if AIRPORTS[code].primary:
            return code
    return sorted(codes)[0]


CITY_PHRASES: tuple[str, ...] = tuple(
    sorted(_CITY_INDEX.keys(), key=lambda phrase: (-len(phrase.split()), phrase))
)


def get(code: str | None) -> Airport | None:
    if not code:
        return None
    return AIRPORTS.get(code.strip().upper())


def is_known(code: str | None) -> bool:
    return get(code) is not None


def resolve(text: str | None) -> str | None:
    """Turn free text ("MIA", "miami", "the big apple") into one IATA code."""
    if not text:
        return None
    raw = text.strip()
    if len(raw) == 3 and raw.upper() in AIRPORTS:
        return raw.upper()
    folded = _fold(raw)
    if not folded:
        return None
    if folded.upper() in AIRPORTS:
        return folded.upper()
    codes = _CITY_INDEX.get(folded)
    if codes:
        return _primary_of(codes)
    # "miami international", "london heathrow" and friends
    for code, airport in AIRPORTS.items():
        if _fold(airport.name) == folded or _fold(f"{airport.city} {airport.name}") == folded:
            return code
    return None


def city_codes(city_phrase: str) -> list[str]:
    return list(_CITY_INDEX.get(_fold(city_phrase), []))


def search(query: str, limit: int = 8) -> list[dict]:
    """Rank airports for the typeahead. Exact code match always wins."""
    folded = _fold(query)
    if not folded:
        return []
    scored: list[tuple[int, str, dict]] = []
    for code, airport in AIRPORTS.items():
        city = _fold(airport.city)
        name = _fold(airport.name)
        country = _fold(airport.country)
        score: int | None = None
        if code.lower() == folded:
            score = 0
        elif city == folded:
            score = 1
        elif city.startswith(folded):
            score = 2
        elif code.lower().startswith(folded):
            score = 3
        elif name.startswith(folded):
            score = 4
        elif folded in city or folded in name:
            score = 5
        elif country.startswith(folded):
            score = 6
        if score is None:
            for alias, alias_city in _CITY_ALIASES.items():
                if _fold(alias).startswith(folded) and _fold(alias_city) == city:
                    score = 5
                    break
        if score is not None:
            if not airport.primary:
                score += 1
            scored.append((score, code, airport.to_dict()))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored[:limit]]


def distance_km(origin: str, destination: str) -> float:
    """Great-circle distance between two known airports."""
    a, b = get(origin), get(destination)
    if a is None or b is None:
        return 0.0
    radius = 6371.0
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))
