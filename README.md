# Wanderlust AI — Travel & Itinerary Concierge

![Wanderlust AI Demo](./demo.gif)

**Wanderlust AI** is a conversational AI travel concierge powered by Google Cloud's Agent Development Kit (ADK) and Vertex AI Agent Platform. It helps travelers discover destinations, plan personalized vacation itineraries, generate scenic images and video previews, check live weather, search nearby attractions, and calculate trip budgets.

---

## Capabilities & Implemented Features

### 1. Catalog & Database Lookup
- **`list_destinations`**: Queries travel destinations from Google Cloud Firestore, filtered by category (*Culture & Heritage*, *Beach & Coastal*, *Nature & Adventure*, *City & Arts*).
- **`add_destination`**: Adds new travel destination documents and highlights directly to Firestore.

### 2. Generative Media & Visuals
- **`generate_destination_image`**: Generates high-quality travel preview images using the `gemini-3.1-flash-lite-image` model in the `global` region. Images are saved as session artifacts and uploaded to a public Google Cloud Storage bucket.
- **`generate_destination_video`**: Generates short travel video clips using the `gemini-omni-flash-preview` model via the Vertex AI Interactions API. Videos are saved as session artifacts and published to Cloud Storage.

### 3. Maps & Location Intelligence
- **`geocode_address`**: Converts location names or street addresses into precise geographic coordinates using the Google Maps Geocoding API.
- **`find_nearby_places`**: Discovers nearby tourist attractions, hotels, museums, and restaurants using the Google Places API (New).

### 4. Real-time Weather & Local Time
- **`get_live_destination_weather`**: Retrieves live temperature and wind forecasts for any global destination via Open-Meteo.
- **`get_current_time`**: Returns current local time for requested destinations.

### 5. Budget Calculations & Code Execution
- **`calculate_trip_budget`**: Calculates itemized daily trip cost breakdowns (lodging, dining, activities, local transport) based on travel style (*budget*, *standard*, *luxury*).
- **Agent Sandbox**: Executes Python calculations safely inside an `AgentEngineSandboxCodeExecutor`.

### 6. Memory & Personalized UI
- **Vertex AI Memory Bank**: Preserves user travel preferences, budget constraints, and dietary requirements across sessions using `VertexAiMemoryBankService`.
- **A2UI Interactive Cards**: Renders clean, structured UI cards in responses using `A2uiSchemaManager` (v0.8) and the Basic Catalog.

---

## Google Cloud Services Integration

| Service | Purpose |
| :--- | :--- |
| **Vertex AI Agent Engine** | Remote agent execution runtime, Memory Bank, and Code Executor sandbox |
| **Google Cloud Firestore** | Destination catalog storage (`destinations` collection) |
| **Google Cloud Storage** | Public storage bucket for generated images and video clips |
| **Gemini Models** | `gemini-flash-latest` (Chat), `gemini-3.1-flash-lite-image` (Images), `gemini-omni-flash-preview` (Video) |
| **Google Maps Platform** | Geocoding API and Places API (New) |

---

## Local Setup & Execution

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip install uv`)
- Google Cloud Service Account credentials with Vertex AI, Firestore, and Storage permissions

### Environment Variables
Create a `.env` file in the project root:
```env
GOOGLE_MAPS_API_KEY="your_google_maps_api_key"
```

### Installation
```bash
# Install dependencies
uv sync
```

### Running Locally

1. **Agent Playground (ADK Web)**:
   ```bash
   uv run adk web . --port 8080 --reload_agents
   ```

2. **Custom FastAPI Frontend Proxy**:
   ```bash
   cd frontend
   uv pip install -r requirements.txt
   uv run python main.py
   ```

---

## Project Structure

```
.
├── app/
│   ├── agent.py          # Root ADK agent, tools, and A2UI callbacks
│   └── a2ui_utils.py     # A2UI response formatting callback
├── frontend/
│   ├── main.py           # FastAPI backend proxy to Agent Engine
│   ├── requirements.txt  # Frontend dependencies
│   ├── Dockerfile        # Container build definition for Cloud Run
│   └── static/
│       └── index.html    # Wanderlust AI chat UI & A2UI renderer
├── pyproject.toml        # ADK project dependencies
└── agents-cli-manifest.yaml # Deployment manifest
```
