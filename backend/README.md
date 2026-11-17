# Starstruck calculation service

This is implemented source, not a verified production deployment. The frontend remains usable when the engine is unavailable. No AI service is required for chart calculations.

## Local setup

Use Python 3.12. Create a virtual environment, install requirements.txt, and run `uvicorn service:app --host 127.0.0.1 --port 8000 --no-access-log` from this directory. Run `python -m unittest discover -s tests` for standard-library tests. `tests/test_swiss_integration.py` requires pyswisseph and complete ephemeris files; skips are not astronomical verification.

## Configuration

- ENGINE_ENABLED: leave false until validation, licensing, and rate limits are complete.
- SWISSEPH_LICENSE_MODE: professional or agpl; setting a variable does not grant a license. Resolve Astrodienst's licensing terms and the Python binding's licensing before activation.
- EPHEMERIS_PATH: absolute path to a directory containing licensed/downloaded Swiss Ephemeris data. Mount these at deployment. Provision sepl_18.se1 and semo_18.se1 for supported 1800–2399 planetary dates, seas_18.se1 for the main minor bodies, sefstars.txt for Algol, and numbered asteroid files in their appropriate astN directories. See official documentation for exact file coverage, file names, and layouts. Keep provenance and checksums for downloaded data.
- GEOAPIFY_API_KEY: private server-side key. Use city-only autocomplete; birth date/time are never sent to Geoapify.
- ALLOWED_ORIGINS: comma-separated exact frontend origins, with no trailing slashes. Include your custom domain when connected.

## Deploy

The repository root contains a Render Blueprint (`render.yaml`). Import this repository as a Blueprint in Render to create the Docker web service. Review Render's selected instance and any charges before creating it. The first deployment deliberately starts with calculations disabled. `/health` confirms the service is reachable; `enabled: false` means calculations are not active.

After deployment, add `api.starstruckastro.com` as a custom domain in the service, then add the exact DNS record Render provides in Cloudflare. The initial `onrender.com` HTTPS address also works while DNS is being configured. These are proposed addresses until the host confirms them.

The Docker build installs dependencies and runs `install_ephemeris.py --directory /app/ephe --asteroids`. It downloads core data from a pinned official Astrodienst repository revision and additional asteroid files from the mirror linked in Astrodienst's download documentation. A manifest records URLs, byte counts, and SHA-256 hashes. Failed downloads fail the build. No persistent disk is required for these baked-in files. `.dockerignore` excludes partial local data. Configure the Geoapify secret, complete licensing and validation, and enforce edge rate limits before setting `ENGINE_ENABLED=true`. The Docker build has not been verified in this environment.

For a network-enabled local machine: create a Python 3.12 virtual environment, run `python -m pip install -r requirements.txt`, then `python install_ephemeris.py --asteroids`. Set `EPHEMERIS_PATH` to the resulting absolute `ephe` directory and run the tests. Do not treat successful downloads as astronomical verification.

Frontend integration: copy `birth-profile.js` and `engine-client.js` to the deployed app assets, load them in that order after the existing app script, and add `<meta name="chart-api-base" content="https://YOUR-CONFIRMED-ENGINE-HOST">` in the head. It intercepts the birth form submission, requires selection of a location result, and emits `starstruck:chart-calculated` with `{chart, birthInput}`. Changes clear stale results and emit `starstruck:chart-cleared`. Never set the hostname before testing the deployed API. The adapter is not automatically injected into any current preview by this commit.

The Dockerfile runs on a Python/Docker-capable host. Static Cloudflare Pages cannot execute this Python service. Provide the above secrets through hosting environment settings, mount the ephemeris data, configure TLS and edge rate limits, then set the frontend `chart-api-base` meta tag to the HTTPS service origin. Never add an API secret to frontend HTML.

Before enabling public traffic, enforce edge rate limits on `/api/chart` and `/api/locations`, reject oversized bodies at the proxy, avoid logging birth details, set resource/time limits, and inspect hosting retention/privacy settings. The app does not create accounts or a database.

## API

GET /api/locations?q=Sandpoint returns selectable city labels, coordinates, IANA timezone, and attribution.

POST /api/chart accepts date, time, latitude, longitude, timezone, tradition (`tropical` or `sidereal`), house_system (`W`), unknown_time (boolean), optional fold (0 or 1 for repeated times), and points (supported names in chart_engine.py). Do not send a name.

A successful chart returns normalized longitude, sign, degree, Whole Sign house, retrograde, angles, cusps and major planet aspects. Requested unavailable bodies are explicitly listed. There are no invented asteroid positions. Algol is a fixed star; no catastrophe predictions are generated.

Unknown times use local noon only as a reference, omit houses, angles, Fortune and aspects, and return the Moon's range over that local calendar day. DST gaps are rejected. Repeated times require fold selection. Pre-1970 historical timezone data can have limitations; independently verify unusual historical cases.

## Validation still required

Compare tropical and Lahiri positions, Rising/MC, day/night Fortune, every selected asteroid, and Algol against independent reference charts over the supported date range. Check real Geoapify responses, HTTP endpoint behavior, deployed CORS, input rate limits, and real browser submission. Local arithmetic tests do not prove ephemeris accuracy.

`birth-profile.js` exposes a read-only `StarstruckBirthProfile.get()` snapshot for Personal Insights and Movement, plus `getHumanDesignInput()` for a future Human Design provider. A calculated astrology chart does not establish Human Design results. Input edits clear all derived placement controls, deletion clears the shared profile, and storage events sync tabs. Daily energy, capacity, available time, and movement preference remain user choices.
