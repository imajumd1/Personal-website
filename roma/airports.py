"""A hand-maintained airport table: IATA code, city, country, coordinates, aliases.

Coordinates are here because the simulated fare provider prices on great-circle
distance, and because "is this a real airport?" is the first validation gate.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    city: str
    country: str
    lat: float
    lon: float
    aliases: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.city} ({self.code}) — {self.name}"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "label": self.label,
        }


# code, name, city, country, lat, lon, aliases
_ROWS = [
    ("SFO", "San Francisco International", "San Francisco", "United States", 37.6213, -122.3790, ("bay area", "sf")),
    ("OAK", "Oakland International", "Oakland", "United States", 37.7213, -122.2207, ()),
    ("SJC", "Norman Y. Mineta San Jose International", "San Jose", "United States", 37.3639, -121.9289, ("silicon valley",)),
    ("LAX", "Los Angeles International", "Los Angeles", "United States", 33.9416, -118.4085, ("la",)),
    ("SAN", "San Diego International", "San Diego", "United States", 32.7338, -117.1933, ()),
    ("LAS", "Harry Reid International", "Las Vegas", "United States", 36.0840, -115.1537, ("vegas",)),
    ("PHX", "Phoenix Sky Harbor International", "Phoenix", "United States", 33.4342, -112.0116, ()),
    ("SEA", "Seattle-Tacoma International", "Seattle", "United States", 47.4502, -122.3088, ("sea-tac",)),
    ("PDX", "Portland International", "Portland", "United States", 45.5898, -122.5951, ()),
    ("DEN", "Denver International", "Denver", "United States", 39.8561, -104.6737, ()),
    ("SLC", "Salt Lake City International", "Salt Lake City", "United States", 40.7899, -111.9791, ()),
    ("DFW", "Dallas/Fort Worth International", "Dallas", "United States", 32.8998, -97.0403, ("fort worth", "dallas fort worth")),
    ("AUS", "Austin-Bergstrom International", "Austin", "United States", 30.1975, -97.6664, ()),
    ("IAH", "George Bush Intercontinental", "Houston", "United States", 29.9902, -95.3368, ()),
    ("MSP", "Minneapolis-Saint Paul International", "Minneapolis", "United States", 44.8848, -93.2223, ("saint paul",)),
    ("ORD", "O'Hare International", "Chicago", "United States", 41.9742, -87.9073, ("ohare", "o hare")),
    ("MDW", "Midway International", "Chicago", "United States", 41.7868, -87.7522, ()),
    ("DTW", "Detroit Metropolitan Wayne County", "Detroit", "United States", 42.2124, -83.3534, ()),
    ("ATL", "Hartsfield-Jackson Atlanta International", "Atlanta", "United States", 33.6407, -84.4277, ()),
    ("MIA", "Miami International", "Miami", "United States", 25.7959, -80.2870, ()),
    ("FLL", "Fort Lauderdale-Hollywood International", "Fort Lauderdale", "United States", 26.0742, -80.1506, ()),
    ("MCO", "Orlando International", "Orlando", "United States", 28.4312, -81.3081, ()),
    ("TPA", "Tampa International", "Tampa", "United States", 27.9755, -82.5332, ()),
    ("CLT", "Charlotte Douglas International", "Charlotte", "United States", 35.2144, -80.9473, ()),
    ("BNA", "Nashville International", "Nashville", "United States", 36.1263, -86.6774, ()),
    ("JFK", "John F. Kennedy International", "New York", "United States", 40.6413, -73.7781, ("nyc", "new york city")),
    ("LGA", "LaGuardia", "New York", "United States", 40.7769, -73.8740, ()),
    ("EWR", "Newark Liberty International", "Newark", "United States", 40.6895, -74.1745, ("new jersey",)),
    ("BOS", "Logan International", "Boston", "United States", 42.3656, -71.0096, ()),
    ("PHL", "Philadelphia International", "Philadelphia", "United States", 39.8744, -75.2424, ("philly",)),
    ("DCA", "Ronald Reagan Washington National", "Washington", "United States", 38.8512, -77.0402, ("washington dc", "dc")),
    ("IAD", "Washington Dulles International", "Washington", "United States", 38.9531, -77.4565, ("dulles",)),
    ("BWI", "Baltimore/Washington International", "Baltimore", "United States", 39.1774, -76.6684, ()),
    ("HNL", "Daniel K. Inouye International", "Honolulu", "United States", 21.3187, -157.9225, ("hawaii", "oahu")),
    ("OGG", "Kahului", "Maui", "United States", 20.8986, -156.4305, ("kahului",)),
    ("ANC", "Ted Stevens Anchorage International", "Anchorage", "United States", 61.1743, -149.9962, ("alaska",)),
    ("YVR", "Vancouver International", "Vancouver", "Canada", 49.1967, -123.1815, ()),
    ("YYZ", "Toronto Pearson International", "Toronto", "Canada", 43.6777, -79.6248, ()),
    ("YUL", "Montreal-Trudeau International", "Montreal", "Canada", 45.4706, -73.7408, ()),
    ("MEX", "Mexico City International", "Mexico City", "Mexico", 19.4363, -99.0721, ()),
    ("CUN", "Cancun International", "Cancun", "Mexico", 21.0365, -86.8771, ()),
    ("GRU", "Sao Paulo-Guarulhos International", "Sao Paulo", "Brazil", -23.4356, -46.4731, ("sao paolo",)),
    ("GIG", "Rio de Janeiro-Galeao International", "Rio de Janeiro", "Brazil", -22.8100, -43.2506, ("rio",)),
    ("EZE", "Ministro Pistarini International", "Buenos Aires", "Argentina", -34.8222, -58.5358, ()),
    ("SCL", "Arturo Merino Benitez International", "Santiago", "Chile", -33.3930, -70.7858, ()),
    ("LIM", "Jorge Chavez International", "Lima", "Peru", -12.0219, -77.1143, ()),
    ("BOG", "El Dorado International", "Bogota", "Colombia", 4.7016, -74.1469, ()),
    ("PTY", "Tocumen International", "Panama City", "Panama", 9.0714, -79.3835, ()),
    ("LHR", "Heathrow", "London", "United Kingdom", 51.4700, -0.4543, ("heathrow",)),
    ("LGW", "Gatwick", "London", "United Kingdom", 51.1537, -0.1821, ("gatwick",)),
    ("STN", "Stansted", "London", "United Kingdom", 51.8860, 0.2389, ()),
    ("MAN", "Manchester", "Manchester", "United Kingdom", 53.3650, -2.2727, ()),
    ("EDI", "Edinburgh", "Edinburgh", "United Kingdom", 55.9500, -3.3725, ("scotland",)),
    ("DUB", "Dublin", "Dublin", "Ireland", 53.4213, -6.2701, ()),
    ("CDG", "Charles de Gaulle", "Paris", "France", 49.0097, 2.5479, ("charles de gaulle",)),
    ("ORY", "Orly", "Paris", "France", 48.7233, 2.3794, ()),
    ("NCE", "Cote d'Azur", "Nice", "France", 43.6584, 7.2159, ()),
    ("AMS", "Schiphol", "Amsterdam", "Netherlands", 52.3105, 4.7683, ("schiphol",)),
    ("BRU", "Brussels", "Brussels", "Belgium", 50.9010, 4.4844, ()),
    ("FRA", "Frankfurt", "Frankfurt", "Germany", 50.0379, 8.5622, ()),
    ("MUC", "Munich", "Munich", "Germany", 48.3537, 11.7750, ("munchen",)),
    ("BER", "Brandenburg", "Berlin", "Germany", 52.3667, 13.5033, ()),
    ("ZRH", "Zurich", "Zurich", "Switzerland", 47.4647, 8.5492, ()),
    ("GVA", "Geneva", "Geneva", "Switzerland", 46.2381, 6.1089, ()),
    ("VIE", "Vienna", "Vienna", "Austria", 48.1103, 16.5697, ("wien",)),
    ("CPH", "Copenhagen", "Copenhagen", "Denmark", 55.6180, 12.6560, ()),
    ("ARN", "Arlanda", "Stockholm", "Sweden", 59.6498, 17.9238, ()),
    ("OSL", "Oslo Gardermoen", "Oslo", "Norway", 60.1976, 11.1004, ()),
    ("HEL", "Helsinki-Vantaa", "Helsinki", "Finland", 60.3172, 24.9633, ()),
    ("MAD", "Adolfo Suarez Madrid-Barajas", "Madrid", "Spain", 40.4983, -3.5676, ()),
    ("BCN", "Josep Tarradellas Barcelona-El Prat", "Barcelona", "Spain", 41.2974, 2.0833, ()),
    ("LIS", "Humberto Delgado", "Lisbon", "Portugal", 38.7742, -9.1342, ()),
    # No "roma" alias for Rome: the agent answers to that name in chat.
    ("FCO", "Fiumicino", "Rome", "Italy", 41.8003, 12.2389, ("fiumicino",)),
    ("MXP", "Malpensa", "Milan", "Italy", 45.6306, 8.7281, ("milano",)),
    ("VCE", "Marco Polo", "Venice", "Italy", 45.5053, 12.3519, ("venezia",)),
    ("ATH", "Athens International", "Athens", "Greece", 37.9364, 23.9445, ()),
    ("IST", "Istanbul", "Istanbul", "Turkey", 41.2753, 28.7519, ()),
    ("PRG", "Vaclav Havel", "Prague", "Czechia", 50.1008, 14.2600, ("praha",)),
    ("WAW", "Chopin", "Warsaw", "Poland", 52.1657, 20.9671, ()),
    ("BUD", "Budapest Ferenc Liszt", "Budapest", "Hungary", 47.4369, 19.2556, ()),
    ("KEF", "Keflavik", "Reykjavik", "Iceland", 63.9850, -22.6056, ("iceland",)),
    ("DXB", "Dubai International", "Dubai", "United Arab Emirates", 25.2532, 55.3657, ()),
    ("AUH", "Zayed International", "Abu Dhabi", "United Arab Emirates", 24.4330, 54.6511, ()),
    ("DOH", "Hamad International", "Doha", "Qatar", 25.2731, 51.6081, ()),
    ("TLV", "Ben Gurion", "Tel Aviv", "Israel", 32.0114, 34.8867, ()),
    ("CAI", "Cairo International", "Cairo", "Egypt", 30.1219, 31.4056, ()),
    ("JNB", "O. R. Tambo International", "Johannesburg", "South Africa", -26.1392, 28.2460, ()),
    ("CPT", "Cape Town International", "Cape Town", "South Africa", -33.9715, 18.6021, ()),
    ("NBO", "Jomo Kenyatta International", "Nairobi", "Kenya", -1.3192, 36.9278, ()),
    ("LOS", "Murtala Muhammed International", "Lagos", "Nigeria", 6.5774, 3.3212, ()),
    ("DEL", "Indira Gandhi International", "Delhi", "India", 28.5562, 77.1000, ("new delhi",)),
    ("BOM", "Chhatrapati Shivaji Maharaj International", "Mumbai", "India", 19.0896, 72.8656, ("bombay",)),
    ("BLR", "Kempegowda International", "Bangalore", "India", 13.1986, 77.7066, ("bengaluru",)),
    ("MAA", "Chennai International", "Chennai", "India", 12.9941, 80.1709, ("madras",)),
    ("HYD", "Rajiv Gandhi International", "Hyderabad", "India", 17.2403, 78.4294, ()),
    ("CCU", "Netaji Subhas Chandra Bose International", "Kolkata", "India", 22.6547, 88.4467, ("calcutta",)),
    ("KTM", "Tribhuvan International", "Kathmandu", "Nepal", 27.6966, 85.3591, ()),
    ("CMB", "Bandaranaike International", "Colombo", "Sri Lanka", 7.1808, 79.8841, ()),
    ("SIN", "Changi", "Singapore", "Singapore", 1.3644, 103.9915, ("changi",)),
    ("BKK", "Suvarnabhumi", "Bangkok", "Thailand", 13.6900, 100.7501, ()),
    ("HKT", "Phuket International", "Phuket", "Thailand", 8.1132, 98.3169, ()),
    ("KUL", "Kuala Lumpur International", "Kuala Lumpur", "Malaysia", 2.7456, 101.7099, ()),
    ("CGK", "Soekarno-Hatta International", "Jakarta", "Indonesia", -6.1256, 106.6559, ()),
    ("DPS", "Ngurah Rai International", "Denpasar", "Indonesia", -8.7482, 115.1672, ("bali",)),
    ("MNL", "Ninoy Aquino International", "Manila", "Philippines", 14.5086, 121.0198, ()),
    ("HAN", "Noi Bai International", "Hanoi", "Vietnam", 21.2212, 105.8072, ()),
    ("SGN", "Tan Son Nhat International", "Ho Chi Minh City", "Vietnam", 10.8188, 106.6520, ("saigon",)),
    ("HKG", "Hong Kong International", "Hong Kong", "Hong Kong", 22.3080, 113.9185, ()),
    ("TPE", "Taoyuan International", "Taipei", "Taiwan", 25.0777, 121.2328, ()),
    ("PVG", "Pudong International", "Shanghai", "China", 31.1443, 121.8083, ()),
    ("PEK", "Beijing Capital International", "Beijing", "China", 40.0799, 116.6031, ()),
    ("CAN", "Baiyun International", "Guangzhou", "China", 23.3924, 113.2988, ()),
    ("ICN", "Incheon International", "Seoul", "South Korea", 37.4602, 126.4407, ("seoul incheon",)),
    ("NRT", "Narita International", "Tokyo", "Japan", 35.7720, 140.3929, ("narita",)),
    ("HND", "Haneda", "Tokyo", "Japan", 35.5494, 139.7798, ("haneda",)),
    ("KIX", "Kansai International", "Osaka", "Japan", 34.4273, 135.2444, ("osaka kansai",)),
    ("CTS", "New Chitose", "Sapporo", "Japan", 42.7752, 141.6923, ()),
    ("SYD", "Kingsford Smith", "Sydney", "Australia", -33.9399, 151.1753, ()),
    ("MEL", "Melbourne", "Melbourne", "Australia", -37.6690, 144.8410, ()),
    ("BNE", "Brisbane", "Brisbane", "Australia", -27.3842, 153.1175, ()),
    ("PER", "Perth", "Perth", "Australia", -31.9385, 115.9672, ()),
    ("AKL", "Auckland", "Auckland", "New Zealand", -37.0082, 174.7850, ()),
    ("NAN", "Nadi International", "Nadi", "Fiji", -17.7554, 177.4434, ("fiji",)),
]

AIRPORTS: dict[str, Airport] = {
    row[0]: Airport(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in _ROWS
}

# City-name → primary airport. First listed airport for a city wins, so "London"
# resolves to LHR and "Tokyo" to NRT.
_CITY_INDEX: dict[str, str] = {}
for _code, _airport in AIRPORTS.items():
    for _key in (_airport.city.lower(), *(a.lower() for a in _airport.aliases)):
        _CITY_INDEX.setdefault(_key, _code)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower()).strip()


def lookup_airport(text: str) -> Airport | None:
    """Resolve an IATA code, city name, or known alias to an :class:`Airport`."""
    raw = str(text or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in AIRPORTS:
        return AIRPORTS[upper]

    # "San Francisco (SFO) — ..." from the typeahead
    match = re.search(r"\(([A-Z]{3})\)", upper)
    if match and match.group(1) in AIRPORTS:
        return AIRPORTS[match.group(1)]

    key = _norm(raw)
    if key in _CITY_INDEX:
        return AIRPORTS[_CITY_INDEX[key]]

    # Trailing bare code, e.g. "London LHR"
    tokens = key.split()
    if tokens and tokens[-1].upper() in AIRPORTS:
        return AIRPORTS[tokens[-1].upper()]
    return None


def search_airports(query: str, limit: int = 8) -> list[Airport]:
    """Typeahead: exact code, then city prefix, then substring matches."""
    key = _norm(query)
    if not key:
        return []
    exact: list[Airport] = []
    prefix: list[Airport] = []
    contains: list[Airport] = []
    for airport in AIRPORTS.values():
        code = airport.code.lower()
        city = airport.city.lower()
        name = airport.name.lower()
        aliases = " ".join(airport.aliases).lower()
        if code == key:
            exact.append(airport)
        elif city.startswith(key) or code.startswith(key):
            prefix.append(airport)
        elif key in city or key in name or key in aliases or key in airport.country.lower():
            contains.append(airport)
    ordered = exact + sorted(prefix, key=lambda a: a.city) + sorted(contains, key=lambda a: a.city)
    return ordered[:limit]


def distance_km(a: Airport, b: Airport) -> float:
    """Great-circle distance, used to price simulated fares."""
    radius = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def city_tokens() -> list[tuple[str, str]]:
    """(searchable phrase, IATA code) pairs, longest phrase first — for intent parsing."""
    # setdefault keeps the same "first airport listed for a city wins" rule as
    # _CITY_INDEX, so "Tokyo" means the same airport everywhere in Roma.
    pairs: dict[str, str] = {}
    for code, airport in AIRPORTS.items():
        pairs.setdefault(airport.city.lower(), code)
        for alias in airport.aliases:
            pairs.setdefault(alias.lower(), code)
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))
