import pandas as pd
import json
import time
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Load or create cache
COORDS_FILE = "station_coords.json"
if os.path.exists(COORDS_FILE):
    with open(COORDS_FILE, "r") as f:
        station_coords = json.load(f)
else:
    station_coords = {}

# Load stations
df = pd.read_csv("metro.csv")
stations = set(df['From Station']).union(set(df['To Station']))

geolocator = Nominatim(user_agent="metro-route-optimizer")

def geocode_station(station):
    queries = [
        f"{station} Metro Station, Delhi, India",
        f"{station}, Delhi Metro",
        f"{station}, India"
    ]
    for query in queries:
        try:
            print(f"🔍 Trying: {query}")
            location = geolocator.geocode(query, timeout=10)
            if location:
                print(f"✅ Found: {station} → {location.latitude}, {location.longitude}")
                return {"lat": location.latitude, "lon": location.longitude}
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"⚠️ Error: {station} – {e}")
        time.sleep(1)
    print(f"❌ Not found: {station}")
    return None

# Main loop
for station in stations:
    if station_coords.get(station):
        print(f"✅ Cached: {station}")
        continue
    station_coords[station] = geocode_station(station)
    time.sleep(1)

# Save results
with open(COORDS_FILE, "w") as f:
    json.dump(station_coords, f, indent=4)

print("\n🗺️ Done! Coordinates saved to station_coords.json.")
