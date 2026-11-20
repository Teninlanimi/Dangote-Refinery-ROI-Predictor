# Free deployment (Neon + GitHub Actions + Render)

Live online at no cost, with no card and no expiry date. Three free services,
each doing one job:

```
 GitHub Actions (06:05 & 18:05 UTC)        Render (free web service)
 runs  python -m pipeline.ingest           runs  gunicorn app:app
          │  writes                                  │  reads
          └──────────────►  Neon Postgres  ◄─────────┘
                            (free, never expires)
```

| Service | Job | Free-plan catch |
|---|---|---|
| **Neon** | PostgreSQL database | 1 GB storage per project. Years of daily prices use a few MB. |
| **GitHub Actions** | Runs the data pipeline on a schedule | GitHub pauses schedules in a repo with no activity for 60 days; you get an email and one click turns it back on. |
| **Render** | Hosts the website | Sleeps after 15 minutes without visitors; the next visit takes up to a minute to wake it. |

Because the pipeline runs on GitHub, not on Render, the data keeps updating even
while the website sleeps.

Do the steps in this order: database first, then data, then website.

---

## 1. Create the database on Neon (5 min)

1. Go to https://neon.com and sign up with your GitHub account.
2. Create a project: name `dangote-roi`, region **AWS Europe Central (Frankfurt)**
   (the closest to Lagos), latest Postgres version.
3. On the project dashboard click **Connect**. Turn **Connection pooling off**,
   then copy the connection string. It looks like:
   ```
   postgresql://neondb_owner:abc123@ep-cool-name-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
   Keep it somewhere private: it contains the database password. The app
   accepts it exactly as Neon gives it.

The tables are created automatically on the first run, so there is nothing to
set up inside Neon.

## 2. Fill the database with GitHub Actions (5 min)

1. Open your repo on GitHub → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**. Add two secrets:
   - `DATABASE_URL`: the Neon connection string from step 1
   - `FRED_API_KEY`: your FRED key (the same one in your local `.env`)
2. Go to the **Actions** tab → **Ingest market data** (left sidebar) →
   **Run workflow** → **Run workflow**.
3. After about a minute the run should go green. Click it and open the
   **Run pipeline** step: you'll see the same JSON summary you saw locally,
   with about 666 rows inserted on the first run.

From now on it runs by itself at 07:05 and 19:05 Lagos time.

## 3. Put the website on Render (10 min)

1. Go to https://render.com and sign up with your GitHub account.
2. Click **New** → **Blueprint**, pick the `Dangote-Refinery-ROI-Predictor`
   repo, and Render reads `render.yaml`.
3. It asks for `DATABASE_URL`: paste the same Neon connection string.
   Click **Apply**.
4. The first build takes a few minutes. When it says **Live**, open the
   `https://dangote-refinery-roi-predictor.onrender.com` link (Render shows
   the exact address).

Check three pages:
- `/` shows the live market figures
- `/status` lists the GitHub Actions run(s)
- `/health` returns `"status": "ok"` and `"database": "ok"`

Every push to `main` redeploys the site automatically.

## Day-to-day

| Task | Where |
|---|---|
| Pull data now | GitHub → Actions → Ingest market data → Run workflow |
| See pipeline history | your site's `/status` page, or the Actions tab |
| Look at the raw data | Neon dashboard → **Tables** (or **SQL Editor**: `select * from market_observations order by observed_on desc limit 20;`) |
| Website logs | Render dashboard → your service → **Logs** |

## Troubleshooting

- **Ingest run fails with "FRED_API_KEY is not set":** the secret name must be
  exactly `FRED_API_KEY`, added under *Actions* secrets (not *Codespaces*).
- **Run fails with a connection error:** re-copy the Neon string with pooling
  off, and check the secret has no spaces or quotes around it.
- **Website shows "No live data yet":** the ingest workflow hasn't succeeded
  yet; run it by hand (step 2).
- **`/health` says degraded:** no successful pipeline run in 36 hours; check
  the Actions tab. If schedules were paused for inactivity, click **Enable workflow**.
- **First visit is slow:** that's Render waking the free service. Normal.

## Moving to AWS later

Nothing in the code changes. `deploy/AWS_DEPLOY.md` runs the same app with
Docker on an EC2 server; you can even keep Neon as the database by putting its
connection string in `DATABASE_URL`.
