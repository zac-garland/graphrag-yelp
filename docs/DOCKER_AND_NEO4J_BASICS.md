# Docker and Neo4j — basics for this project

This guide assumes you’ve never used Docker or Neo4j. It gets you to the point where the graph is loaded and you can run the API.

---

## 1. Install Docker

**What it is:** Docker runs “containers” — small, isolated environments. We use it to run Neo4j the same way on everyone’s machine without installing Neo4j by hand.

**Install:**

- **Mac/Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). Open it and wait until it says it’s running.
- **Linux:** Install the [Docker Engine](https://docs.docker.com/engine/install/) for your distro, then start the service (e.g. `sudo systemctl start docker`).

**Check it works:** In a terminal:

```bash
docker --version
docker run hello-world
```

If you see “Hello from Docker!”, you’re good.

---

## 2. Set a Neo4j password in this project

Neo4j needs a password. We put it in a `.env` file so the app and Docker can use it.

1. In the **project root** (`graphrag-yelp/`), copy the example env file:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor and set a password:

   ```bash
   NEO4J_PASSWORD=YourSecurePassword123
   ```

   Use any password you like (e.g. `neo4j123` for local only). Save the file.

**Important:** Don’t commit `.env` or share it — it’s in `.gitignore`.

---

## 3. Start Neo4j with Docker Compose

**What we’re doing:** Running the Neo4j database in a container using the project’s `docker-compose.yml`.

1. Open a terminal and go to the project root:

   ```bash
   cd /path/to/graphrag-yelp
   ```

2. Start Neo4j:

   ```bash
   docker compose up -d
   ```

   - `up` = create and start the containers.
   - `-d` = run in the background (“detached”).

3. Wait ~10–20 seconds for Neo4j to start. Check that the container is running:

   ```bash
   docker compose ps
   ```

   You should see a service named `neo4j` (or `graphrag-neo4j`) with state “running”.

**If it fails:** Make sure Docker Desktop (or the Docker service) is running and that you created `.env` with `NEO4J_PASSWORD` set.

---

## 4. Open Neo4j in your browser (optional but useful)

Neo4j has a web UI where you can run Cypher and explore the graph.

1. In your browser go to: **http://localhost:7474**
2. **Connect** (or “Connect to Neo4j”).
3. **Login:**
   - **Connect URL:** `bolt://localhost:7687` (usually pre-filled).
   - **Username:** `neo4j`
   - **Password:** the value you put in `.env` for `NEO4J_PASSWORD`.
4. Click **Connect**.

You’re in Neo4j Browser. At first the graph will be empty until you load data (next step).

---

## 5. Load the graph into Neo4j

**What we’re doing:** Running our Python script that reads the CSV files in `data/processed/` and writes nodes and relationships into Neo4j.

**You must have already run the Phase 1 pipeline** so that `data/processed/` contains the CSVs (e.g. `restaurant_projection_nodes.csv`, `city_reviews.csv`, etc.). If not, run the pipeline first (see README or the student setup guide).

1. Activate the project’s Python environment and run the loader:

   ```bash
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   python -m pipeline.load_neo4j
   ```

2. The script will:
   - Create constraints and indexes in Neo4j.
   - Load restaurants, reviewers, communities, categories.
   - Load relationships (REVIEWED, FRIENDS_WITH, SHARED_REVIEWERS, etc.).
   - Print progress (e.g. “Loaded 7508 Restaurant nodes”, “REVIEWED: 500000 edges”).

3. When it finishes without errors, the graph is in Neo4j.

**If you see “Connection refused” or “Authentication failed”:**

- Neo4j might still be starting: wait 30 seconds and run `python -m pipeline.load_neo4j` again.
- Check that `.env` has the **same** `NEO4J_PASSWORD` you used when starting the container (Docker Compose uses it for `NEO4J_AUTH`).

---

## 6. Try a query in Neo4j Browser

In Neo4j Browser (http://localhost:7474), in the query bar at the top, run:

```cypher
MATCH (r:Restaurant) RETURN r.name, r.stars, r.k_core LIMIT 10
```

Click the **Run** (play) button. You should see a table of restaurant names, stars, and k-core. That confirms the data is there.

---

## 7. Useful Docker commands (reference)

| What you want              | Command                    |
|----------------------------|----------------------------|
| Start Neo4j                | `docker compose up -d`     |
| Stop Neo4j                 | `docker compose down`      |
| See if Neo4j is running    | `docker compose ps`        |
| View Neo4j logs            | `docker compose logs neo4j`|
| Stop and remove data       | `docker compose down -v`   |

**“Remove data”** (`-v`): deletes the Neo4j data volume. After that, when you run `docker compose up -d` again, Neo4j starts empty and you’d need to run `python -m pipeline.load_neo4j` again.

---

## 8. Summary checklist

- [ ] Docker installed and running (`docker --version`, `docker run hello-world`).
- [ ] In project root: `.env` created from `.env.example` with `NEO4J_PASSWORD` set.
- [ ] Neo4j started: `docker compose up -d` and `docker compose ps` shows it running.
- [ ] (Optional) Neo4j Browser open at http://localhost:7474, logged in with `neo4j` / your password.
- [ ] Graph loaded: `python -m pipeline.load_neo4j` finished successfully.
- [ ] (Optional) Test query in Neo4j Browser: `MATCH (r:Restaurant) RETURN r LIMIT 10`.

After this you can start the API (`uvicorn api.main:app --reload --port 8081`) and use **POST /api/chat** and the other endpoints.
