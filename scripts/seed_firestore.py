#!/usr/bin/env python3
"""Seed script for travel-concierge Firestore database.

Populates the 'destinations' collection with initial travel destination data.
"""

from google.cloud import firestore

# Hardcoded project ID as required to avoid resolution issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-52f5fd0eb02d"


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)

    destinations = [
        {
            "id": "kyoto",
            "name": "Kyoto",
            "country": "Japan",
            "category": "Culture & Heritage",
            "description": "Ancient temples, traditional wooden houses, cherry blossoms, and serene bamboo groves.",
            "best_season": "Spring / Autumn",
            "avg_daily_budget": 160.0,
            "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Kinkaku-ji (Golden Pavilion)"],
        },
        {
            "id": "amalfi",
            "name": "Amalfi Coast",
            "country": "Italy",
            "category": "Beach & Coastal",
            "description": "Dramatic cliffs, pastel-colored cliffside villages, lemon orchards, and Mediterranean views.",
            "best_season": "Late Spring / Summer",
            "avg_daily_budget": 250.0,
            "highlights": ["Positano cliffside strolls", "Path of the Gods hike", "Ravello gardens"],
        },
        {
            "id": "banff",
            "name": "Banff National Park",
            "country": "Canada",
            "category": "Nature & Adventure",
            "description": "Turquoise glacial lakes, majestic Rocky Mountain peaks, hot springs, and abundant wildlife.",
            "best_season": "Summer / Winter",
            "avg_daily_budget": 180.0,
            "highlights": ["Lake Louise canoeing", "Moraine Lake sunrise", "Icefields Parkway drive"],
        },
        {
            "id": "paris",
            "name": "Paris",
            "country": "France",
            "category": "City & Arts",
            "description": "World-class art galleries, iconic landmarks, culinary excellence, and romantic avenues.",
            "best_season": "Spring / Early Autumn",
            "avg_daily_budget": 220.0,
            "highlights": ["Louvre Museum", "Eiffel Tower", "Seine River Cruise", "Le Marais cafes"],
        },
    ]

    collection_ref = db.collection("destinations")
    for dest in destinations:
        doc_id = dest["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(dest)
        print(f"  ✓ Seeded destination: {dest['name']} ({doc_id})")

    print(f"\nSuccessfully seeded {len(destinations)} destinations into Firestore collection 'destinations'.")


if __name__ == "__main__":
    seed_database()
