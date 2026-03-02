# Student guide: Getting the data and generating processed outputs

This guide walks you through downloading the Yelp dataset, placing it in the repo, and running the pipeline to produce the files in `data/processed/`.

---

## 1. Clone the repo

```bash
git clone https://github.com/zac-garland/graphrag-yelp.git
cd graphrag-yelp
```

---

## 2. Get the Yelp Open Dataset

1. **Go to:** [https://www.yelp.com/dataset](https://www.yelp.com/dataset)
2. **Sign in / create a Yelp account** (required to accept the dataset terms).
3. **Download the dataset** (e.g. “Download JSON” or similar). You’ll get a single file, usually named something like **`yelp_dataset.tar`** or **`yelp_dataset.tar.gz`** (size ~10 GB).
4. **Move the downloaded file** into your project folder (the `graphrag-yelp` folder you cloned).  
   - You can put it in the repo root or in a subfolder; we’ll point the pipeline at the right place in the next step.

---

## 3. Extract and name the folder correctly

The pipeline expects the **JSON files** to live inside a folder. The default path we use is **`Yelp JSON/yelp_dataset`**.

**Option A — Match the default (easiest):**

1. **Extract** the archive (double‑click, or in a terminal: `tar -xf yelp_dataset.tar` or `tar -xzf yelp_dataset.tar.gz`).
2. You should get a folder (often named **`yelp_dataset`**) containing files like:
   - `yelp_academic_dataset_business.json`
   - `yelp_academic_dataset_review.json`
   - `yelp_academic_dataset_user.json`
   - (and possibly checkin, tip, etc.)
3. **Rename or move** so that from the **repo root** you have:
   ```text
   graphrag-yelp/
   └── Yelp JSON/
       └── yelp_dataset/
           ├── yelp_academic_dataset_business.json
           ├── yelp_academic_dataset_review.json
           ├── yelp_academic_dataset_user.json
           └── ...
   ```
   So: create a folder named **`Yelp JSON`** (with a space) in the repo root, put the extracted **`yelp_dataset`** folder inside it.  
   If your extracted folder has a different name, rename it to **`yelp_dataset`** and place it inside **`Yelp JSON`**.

**Option B — Use another location:**

- Put the extracted **`yelp_dataset`** folder anywhere you like (e.g. `data/raw/yelp_dataset`).
- Create a `.env` file in the repo root (copy from `.env.example`) and set:
  ```bash
  YELP_DATA_PATH=data/raw/yelp_dataset
  ```
  (or whatever path from the repo root to the folder that contains the JSON files).

**Important:** The folder that `YELP_DATA_PATH` points to must contain the **`.json`** files directly (e.g. `yelp_academic_dataset_business.json`), not another nested folder.

---

## 4. Python environment and dependencies

From the **repo root** (`graphrag-yelp/`):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

---

## 5. Run the pipeline

With the venv active and the dataset in place:

```bash
python -m pipeline.run
```

- **First run:** Reads Yelp JSON (streaming), builds graphs, computes metrics, runs temporal analysis. The **review file is large** (~5 GB); streaming can take **15–45+ minutes**. **Betweenness centrality** on the restaurant graph can take **a few hours**.
- **Outputs** are written under **`data/processed/`**, including:
  - `city_businesses.csv`, `city_reviews.csv`, `city_users.csv`
  - `bipartite_*.csv`, `restaurant_projection_*.csv`, `reviewer_projection_*.csv`, `friend_*.csv`
  - `temporal_growth.csv`, `hype_events.csv`, `influence_test_results.json`
  - (and related graph/temporal files)

**Optional:** To use a different city (e.g. Tampa, Nashville), set before running:

```bash
export TARGET_CITY=Tampa
python -m pipeline.run
```

Or add `TARGET_CITY=Tampa` to a `.env` file in the repo root.

---

## 6. If you already have the CSVs (skip ingest)

If someone gives you the **`city_*.csv`** files and you only want to re-run network + metrics + temporal (no re-download or re-streaming of Yelp):

1. Put `city_businesses.csv`, `city_reviews.csv`, and `city_users.csv` into **`data/processed/`**.
2. Run:
   ```bash
   python -m pipeline.run --skip-ingest
   ```

---

## Quick checklist

- [ ] Repo cloned
- [ ] Yelp dataset downloaded from [yelp.com/dataset](https://www.yelp.com/dataset)
- [ ] Archive extracted; folder containing the JSON files is named **`yelp_dataset`**
- [ ] That folder lives at **`Yelp JSON/yelp_dataset`** (or you set **`YELP_DATA_PATH`** in `.env`)
- [ ] `.venv` created and activated, `pip install -e .` run
- [ ] `python -m pipeline.run` executed; wait for ingest + metrics (and temporal) to finish
- [ ] Outputs in **`data/processed/`**

The **`Yelp JSON/`** folder is in **`.gitignore`**, so the dataset is never committed. Only code and small refs are in the repo.
