# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext, load_memory, preload_memory
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

load_dotenv()

# Hardcoded project ID and Cloud Storage bucket name strings required for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-03-52f5fd0eb02d"
BUCKET_NAME = "travel-concierge-media-qwiklabs-gcp-03-52f5fd0eb02d"
MEMORY_ENGINE_ID = "456400679620050944"

db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

# Memory service configuration for redeploying to Agent Platform
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location="us-east1",
    agent_engine_id=MEMORY_ENGINE_ID,
)

# Read Reasoning Engine resource ID from deployment_metadata.json to configure AgentEngineSandboxCodeExecutor
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_id = None
if metadata_path.exists():
    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        agent_engine_id = meta.get("remote_agent_runtime_id")

code_executor = (
    AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_id)
    if agent_engine_id
    else None
)

# Build A2UI System Prompt using A2uiSchemaManager version 0.8 and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are Wanderlust AI, a knowledgeable Travel & Itinerary Concierge. Help users discover destinations, plan custom vacation itineraries, generate scenic destination photos, geocode locations, search nearby attractions/restaurants with Google Maps, check live weather, calculate trip budgets, recall user travel preferences from memory, and execute Python code calculations.",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


def list_destinations(category: str = "") -> list[dict]:
    """Lists or filters travel destinations from the Firestore catalog.

    Args:
        category: Optional category filter (e.g. 'Culture & Heritage', 'Beach & Coastal', 'Nature & Adventure', 'City & Arts').

    Returns:
        List of destination dictionary records.
    """
    collection_ref = db.collection("destinations")
    docs = collection_ref.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if category and category.lower() not in data.get("category", "").lower():
            continue
        results.append(data)
    return results


def add_destination(
    name: str,
    country: str,
    category: str,
    description: str,
    best_season: str,
    avg_daily_budget: float,
    highlights: list[str],
) -> str:
    """Adds a new travel destination to the Firestore catalog.

    Args:
        name: Name of the destination (e.g., 'Kyoto').
        country: Country where destination is located (e.g., 'Japan').
        category: Travel category (e.g., 'Culture & Heritage', 'Nature & Adventure').
        description: Brief summary of the destination.
        best_season: Best time of year to visit.
        avg_daily_budget: Average estimated daily budget in USD.
        highlights: List of key attractions or activities.

    Returns:
        Confirmation message with document ID.
    """
    doc_id = name.lower().replace(" ", "_")
    doc_ref = db.collection("destinations").document(doc_id)
    data = {
        "id": doc_id,
        "name": name,
        "country": country,
        "category": category,
        "description": description,
        "best_season": best_season,
        "avg_daily_budget": avg_daily_budget,
        "highlights": highlights,
    }
    doc_ref.set(data)
    return f"Successfully added destination '{name}' to Firestore with ID '{doc_id}'."


def calculate_trip_budget(
    destination_id: str,
    num_days: int = 3,
    num_travelers: int = 1,
    travel_style: str = "standard",
) -> dict:
    """Calculates an itemized trip budget breakdown for a destination.

    Args:
        destination_id: Document ID of destination in Firestore (e.g., 'kyoto', 'amalfi', 'banff', 'paris').
        num_days: Duration of trip in days (default: 3).
        num_travelers: Number of travelers (default: 1).
        travel_style: Budget tier - 'budget' (0.8x), 'standard' (1.0x), or 'luxury' (1.5x).

    Returns:
        Dictionary containing cost breakdown (lodging, dining, activities, transport) and grand total in USD.
    """
    doc_ref = db.collection("destinations").document(destination_id.lower().strip())
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Destination '{destination_id}' not found in catalog."}

    dest_data = doc.to_dict()
    base_daily = dest_data.get("avg_daily_budget", 150.0)

    multiplier = 1.0
    if travel_style.lower() == "budget":
        multiplier = 0.8
    elif travel_style.lower() == "luxury":
        multiplier = 1.5

    daily_per_person = base_daily * multiplier
    total_lodging = round(daily_per_person * 0.45 * num_days * num_travelers, 2)
    total_food = round(daily_per_person * 0.30 * num_days * num_travelers, 2)
    total_activities = round(daily_per_person * 0.15 * num_days * num_travelers, 2)
    total_transport = round(daily_per_person * 0.10 * num_days * num_travelers, 2)
    grand_total = round(total_lodging + total_food + total_activities + total_transport, 2)

    return {
        "destination": dest_data.get("name"),
        "country": dest_data.get("country"),
        "num_days": num_days,
        "num_travelers": num_travelers,
        "travel_style": travel_style,
        "breakdown_usd": {
            "lodging": total_lodging,
            "food_and_dining": total_food,
            "activities_and_tours": total_activities,
            "local_transport": total_transport,
        },
        "total_estimated_usd": grand_total,
    }


async def generate_destination_image(
    prompt: str,
    filename: str = "destination_preview.jpg",
    tool_context: ToolContext = None,
) -> str:
    """Generates a travel image preview for a destination using Gemini 3.1 Flash Lite Image in global region.

    Args:
        prompt: Detailed description of the travel scene to generate (e.g. 'A scenic view of Kyoto Arashiyama bamboo forest').
        filename: Output filename for saved artifact and storage object (default: 'destination_preview.jpg').

    Returns:
        Public HTTPS URL of the generated image stored in Google Cloud Storage.
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return "Error: No image bytes returned from gemini-3.1-flash-lite-image model."

        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            filename = f"{filename}.jpg"

        # 1. Save artifact to Playground's Artifacts panel
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return f"Successfully generated destination image and published to public URL: {public_url}"
    except Exception as e:
        return f"Error generating destination image: {str(e)}"


async def generate_destination_video(
    prompt: str,
    filename: str = "destination_clip.mp4",
    tool_context: ToolContext = None,
) -> str:
    """Generates a short travel video for a destination using Google's Omni model (gemini-omni-flash-preview) in global region.

    Args:
        prompt: Description of the travel video to generate (e.g. 'A scenic short video of waves crashing on a tropical beach in Bali').
        filename: Output filename for saved artifact and storage object (default: 'destination_clip.mp4').

    Returns:
        Public HTTPS URL of the generated video stored in Google Cloud Storage.
    """
    try:
        if not filename.endswith(".mp4"):
            filename = f"{filename}.mp4"

        response = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        if hasattr(response, "output_video") and response.output_video:
            video_bytes = getattr(response.output_video, "data", None)

        if not video_bytes:
            return "Error: No video bytes returned from gemini-omni-flash-preview model."

        # 1. Save artifact to Playground's Artifacts panel
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return f"Successfully generated destination video and published to public URL: {public_url}"
    except Exception as e:
        return f"Error generating destination video: {str(e)}"



def geocode_address(address: str) -> dict:
    """Converts a street address or location name into geographic coordinates using Google Geocoding API.

    Args:
        address: Name of location or street address (e.g., 'Kyoto Station', 'Eiffel Tower, Paris').

    Returns:
        Dictionary containing formatted address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed for '{address}': {data.get('status')}"}

        first_result = data["results"][0]
        location = first_result["geometry"]["location"]
        return {
            "address": first_result.get("formatted_address"),
            "location": {
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
            },
        }
    except Exception as e:
        return {"error": f"Geocoding API request error: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 2000.0,
) -> list[dict]:
    """Finds nearby points of interest (attractions, restaurants, hotels) using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Category of place to search for (e.g. 'restaurant', 'hotel', 'tourist_attraction', 'museum', 'cafe').
        radius_meters: Search radius in meters (default: 2000).

    Returns:
        List of dictionaries with name, address, location (latitude, longitude), rating, and types.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.rating",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        raw_places = data.get("places", [])
        results = []
        for p in raw_places:
            results.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress"),
                "location": p.get("location"),
                "rating": p.get("rating"),
                "types": p.get("types", []),
            })
        return results
    except Exception as e:
        return [{"error": f"Places API request error: {str(e)}"}]


def get_live_destination_weather(location: str) -> str:
    """Fetches real-time live weather data for any destination using the Open-Meteo public API.

    Args:
        location: City or destination name (e.g., 'Kyoto', 'Paris', 'Amalfi', 'Banff').

    Returns:
        String with live temperature in Celsius and Fahrenheit, wind speed, and country name.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "WanderlustAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        results = geo_data.get("results")
        if not results:
            return f"Could not find coordinates for location: {location}"

        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        city_name = place.get("name", location)
        country = place.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "WanderlustAI/1.0"})
        with urllib.request.urlopen(req_w, timeout=5) as resp_w:
            w_data = json.loads(resp_w.read().decode())

        current = w_data.get("current_weather", {})
        temp_c = current.get("temperature")
        temp_f = round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None
        wind_speed = current.get("windspeed")

        return (
            f"Current weather in {city_name}, {country}: "
            f"{temp_c}°C ({temp_f}°F), Wind Speed: {wind_speed} km/h."
        )
    except Exception as e:
        return f"Error fetching live weather for {location}: {str(e)}"


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
    tools=[
        list_destinations,
        add_destination,
        calculate_trip_budget,
        generate_destination_image,
        generate_destination_video,
        geocode_address,

        find_nearby_places,
        get_live_destination_weather,
        get_current_time,
        load_memory,
        preload_memory,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
