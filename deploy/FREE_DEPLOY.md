# Free deployment (Neon + GitHub Actions + Vercel)

Live at **https://dangote-refinery-roi-predictor.vercel.app**, at no cost, with
no card and no expiry date. Three free services, each doing one job:

```
 GitHub Actions (06:05 & 18:05 UTC)        Vercel (free Hobby plan)
 runs  python -m pipeline.ingest           runs  the Flask app (app.py)
          │  writes                                  │  reads
          └──────────────►  Neon Postgres  ◄─────────┘
                            (free, never expires)
```

| Service | Job | Free-plan catch |
|---|---|---|
| **Neon** | PostgreSQL database | 1 GB storage per project. Years of daily prices use a few MB. |
| **GitHub Actions** | Runs the data pipeline on a schedule | GitHub pauses schedules in a repo with no activity for 60 days; you get an email and one click turns it back on. |
| **Vercel** | Hosts the website | Hobby plan is for personal, non-commercial projects. The first visit after a quiet spell can take a few seconds while the function starts. |

Because the pipeline runs on GitHub, not on Vercel, the data keeps updating
whether or not anyone visits the site.

Do the steps in this order: database first, then data, then website.

---

## 1. Create the database on Neon (5 min)

1. Go to https://neon.com and sign up with your GitHub account.
2. Create a project: name `dangote-roi`, region **AWS Europe Central (Frankfurt)**
   (the closest to Lagos), latest Postgres version.
3. Ignore the "Set up this app on Neon" instructions for coding agents (they are
   for JavaScript apps). Instead click **Connect** in the top bar of the project.
   Turn **Connection pooling off** and copy the connection string. It looks like:
   ```
   postgresql://neondb_owner:<password>@ep-xxxx-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
   Keep it private: it contains the database password. Never paste it into code,
   a commit, a chat or a screenshot. The app accepts it exactly as Neon gives it.

The tables are created automatically on the first run, so there is nothing to
set up inside Neon.

## 2. Fill the database with GitHub Actions (5 min)

1. Open the repo on GitHub → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**. Add two secrets:
   - `DATABASE_URL`: the Neon connection string from step 1
   - `FRED_API_KEY`: your FRED key (only the value after `FRED_API_KEY=` in `.env`)
2. Go to the **Actions** tab → **Ingest market data** (left sidebar) →
   **Run workflow** → **Run workflow**
   (direct link: `/actions/workflows/ingest.yml` on the repo).
3. After about a minute the run should go green. Open it and the **Run pipeline**
   step shows the JSON summary, with about 666 rows inserted on the first run.

From now on it runs by itself at 07:05 and 19:05 Lagos time.

## 3. Put the website on Vercel (10 min)

Vercel detects Flask on its own: it finds the `app` object in `app.py` and runs
it as a Vercel Function, so the repo needs no Vercel config file.

1. Go to https://vercel.com → **Sign Up** → choose **Hobby** → **Continue with GitHub**.
2. **Add New… → Project**. If the repo isn't listed, click **Adjust GitHub App
   Permissions**, allow `Dangote-Refinery-ROI-Predictor`, and save.
3. Click **Import** next to the repo. On **Configure Project**:
   - Project name: `dangote-refinery-roi-predictor` (this becomes the address)
   - Framework preset, root directory, build settings: leave as detected
4. Open **Environment Variables** and add:
   - `DATABASE_URL` = the same Neon connection string
   - `TRUST_PROXY` = `1` (Vercel's proxy sets `X-Forwarded-For`; needed for
     per-visitor usage limits)

   The FRED key is not needed here: only the pipeline on GitHub fetches prices.
5. Click **Deploy**. When it finishes, the address is under **Domains**.

Check three pages:
- `/` shows the live market figures
- `/status` lists the GitHub Actions run(s)
- `/health` returns `"status": "ok"` and `"database": "ok"`

Every push to `main` redeploys the site automatically.

## Day-to-day

| Task | Where |
|---|---|
| Pull data now | GitHub → Actions → Ingest market data → Run workflow |
| See pipeline history | the site's `/status` page, or the Actions tab |
| Look at the raw data | Neon → **Tables**, or **SQL Editor**: `select * from market_observations order by observed_on desc limit 20;` |
| Website errors | Vercel → your project → **Logs** (reload the failing page to see its traceback) |
| Change a setting | Vercel → **Settings → Environment Variables**, then **Deployments → ⋯ → Redeploy** |

## Troubleshooting

- **Ingest run fails with "FRED_API_KEY is not set":** the secret name must be
  exactly `FRED_API_KEY`, added under *Actions* secrets (not *Codespaces*).
- **Ingest run fails with a connection error:** re-copy the Neon string with
  pooling off, and check the secret has no spaces or quotes around it.
- **Site shows "No market data has been loaded yet":** the ingest workflow hasn't
  succeeded yet; run it by hand (step 2).
- **"Internal Server Error":** open Vercel **Logs**, reload the page, and read the
  traceback. `/health` tells you whether the database connection itself works.
- **`/health` says degraded:** no successful pipeline run in 36 hours; check the
  Actions tab. If schedules were paused for inactivity, click **Enable workflow**.
- **Reset the database password** (if it was ever exposed): Neon → **Roles** →
  `neondb_owner` → **Reset password**, then update `DATABASE_URL` in both the
  GitHub secret and Vercel, and redeploy on Vercel.

## Alternatives

- **Render:** `render.yaml` is a ready blueprint for a free Render web service.
  Render may ask for a card to verify the account (a $1 hold, refunded).
- **AWS:** `deploy/AWS_DEPLOY.md` runs the same app with Docker on an EC2 server.
  Nothing in the code changes; you can keep Neon as the database by putting its
  connection string in `DATABASE_URL`.
