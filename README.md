# TAQOIS Command & Control

Cyberpunk-Enterprise Streamlit platform for **Toronto Air Quality Operations Intelligence System (TAQOIS)**.

## Features

- **Simulation Engine**
  - Inputs: Traffic Volume, Weather Inversion, Industrial Activity
  - Supplemental controls: Wind Speed, Humidity, Special Event Surge
  - Corridor-level synthetic risk modeling for Toronto hotspots

- **3D Geospatial Command View**
  - Built with **PyDeck**
  - Extruded 3D corridor columns over Toronto
  - Neon-risk visualization and tooltip intelligence

- **Gemini 2.5 Flash as Chief Operations Officer**
  - Generates:
    - Executive Briefings
    - Tactical Response Plans
    - Public Health Advisories
  - Falls back to deterministic local briefings when API key is absent

- **Cyberpunk-Enterprise UI**
  - Dark mode
  - Neon accents
  - Glassmorphism cards
  - High-density command-center layout

## Stack

- Python 3.10+
- Streamlit
- PyDeck
- Pandas
- Google Generative AI SDK

## Run locally

```bash
git clone <your-repo-url>
cd taqois-command-control
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Gemini setup

Create a `.env` file or export an environment variable:

```bash
GEMINI_API_KEY=your_api_key_here
```

The app uses model id:

```text
gemini-2.5-flash
```

## Suggested repo structure

```text
taqois-command-control/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Deployment

### Streamlit Community Cloud
1. Push this repo to GitHub
2. Connect the repo in Streamlit Community Cloud
3. Add `GEMINI_API_KEY` in app secrets
4. Deploy `app.py`

### Render / Railway
Use a Python web service or Streamlit template and set:
- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Notes

This is a smart-city prototype and uses synthetic corridor logic for simulation.
