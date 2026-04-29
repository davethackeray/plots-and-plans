# RSSHub Integration

We have adopted an architecture that separates the web-scraping concerns from the property-scoring backend. Instead of writing custom Python scrapers for every estate agent (which is unmaintainable for 90+ agents), we use **RSSHub**.

## Architecture
1. **RSSHub (Node.js/Puppeteer):** We host a local/cloud instance of RSSHub. For each estate agent, we write a 20-line JavaScript route (using Cheerio) that scrapes the property listing and detail pages, caching the results via Redis.
2. **RSSFeedIngester (Python):** Our Python orchestrator fetches standard JSON feeds from RSSHub (e.g. `http://localhost:1200/realestate/tuscanitas.json`). It extracts the rich metadata, description, and images from the embedded HTML payload.
3. **Heart-Rate Scorer:** The data seamlessly flows into the same scoring algorithm used by the previous scrapers.

## Writing an Agent Route (JavaScript)
Agent routes are located in `rsshub_routes/`. See `rsshub_routes/template.js` for an example.
Each route must export the structured HTML payload our `RSSFeedIngester` expects. It registers via the `rsshub_routes_override.js` file.

## Running Locally

To test agent routes without repeatedly hitting their servers, run RSSHub locally using Docker:

```bash
# Make sure Docker Desktop is running
docker-compose up -d
```

This spins up 3 containers:
1. `rsshub-local`: The feed generator (available on port 1200)
2. `rsshub-redis`: Caches the results of the property detail pages (critical!)
3. `rsshub-browserless`: Runs Puppeteer for rendering Javascript-heavy React/Vue agent websites.

You can then test your feed locally:
`http://localhost:1200/realestate/example-agent.json`

## Production Deployment

We recommend deploying this `docker-compose.yml` to **Render** or **Railway**. Once deployed, simply update your `.env` file for the Daily Show pipeline:

```env
RSSHUB_BASE_URL=https://your-rsshub-instance.up.railway.app
```