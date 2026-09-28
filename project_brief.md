# My agent: Travel & Itinerary Concierge (Wanderlust AI)

One-liner: A conversational travel agent that helps travelers design personalized vacation itineraries with a catalog of destinations, activities, and generated trip visuals.

Tool coverage:
- Memory: Remembers traveler preferences (budget, pace, dietary restrictions, preferred climate, past visited locations).
- Tools: Destination and activity lookup in Firestore, weather forecast check, and custom itinerary builder.
- Catalog/UI: Collection of hotel options, landmark attraction cards, and daily itinerary tables using A2UI.
- Image gen: Generates custom destination previews and scenic activity photos on demand (`gemini-3.1-flash-lite-image`).
- Sandbox: Computes daily budget breakdowns, currency conversions, and travel time estimates in Agent Platform code execution sandbox.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for budget & timezone calculations, live weather API, Google Maps integration.
