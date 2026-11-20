# Deploying to AWS (EC2 + Docker Compose)

This puts the whole system on **one small EC2 server**: the web app, the
scheduler that pulls crude and FX prices, a PostgreSQL database, and Caddy as
the public entry point (with free HTTPS once you add a domain).

```
                 Internet
                    │  :80 / :443
              ┌─────▼─────┐
              │   caddy   │  reverse proxy, automatic HTTPS
              └─────┬─────┘
                    │ :8000
              ┌─────▼─────┐        ┌─────────────┐
              │    web    │◄──────►│     db      │  PostgreSQL 16
              │ (gunicorn)│        │ (volume)    │  history, runs, checks
              └───────────┘        └──────▲──────┘
                                          │
              ┌───────────┐   FRED + open.er-api   (06:05 and 18:05 UTC)
              │ scheduler ├───────────────┘
              └───────────┘
        EC2 t3.micro · Amazon Linux 2023 · Elastic IP
```

**Why this shape:** one server is cheap and simple to understand end to end,
while still having the parts reviewers look for (containers, a real database,
a scheduled job separated from the web process, health checks, backups). The
code only reads `DATABASE_URL`, so moving the database to Amazon RDS later is
a config change rather than a rewrite.

---

## 0. Before you start (10 min)

1. **AWS account.** New accounts get Free Tier credits (up to $200), and
   EC2 usage is paid out of those credits. Note that on the Free *plan* the
   account closes when the plan ends unless you upgrade, so check your plan
   in the Billing console.
2. **Set a budget alert first.** Billing → Budgets → Create budget → "Monthly
   cost budget", $10, alert to your email. (Setting a budget is also one of the
   activities that earns extra credits.)
3. **FRED API key** for Brent, petrol and diesel prices (free, instant):
   https://fred.stlouisfed.org/docs/api/api_key.html
4. **Push this branch to GitHub** (from your PC):
   ```bat
   git push -u origin production-pipeline
   ```

Rough running cost: a t3.micro, a 20 GB disk and a public IPv4 address come to
around $12–15 a month, which the credits cover for a good while. Check the EC2
pricing page for your region before you launch.

## 1. Launch the server

EC2 console → **Launch instance**:

| Setting | Value |
|---|---|
| Name | `dangote-roi` |
| Region | `us-east-1` (cheapest) or `eu-west-1`. `af-south-1` (Cape Town) is closer to Lagos but costs more and must be enabled first. |
| AMI | Amazon Linux 2023 |
| Instance type | `t3.micro` |
| Key pair | Create new → `dangote-key`, type RSA, `.pem` → it downloads; keep it safe |
| Network | Create security group: **SSH (22) from My IP**, **HTTP (80) from anywhere**, **HTTPS (443) from anywhere** |
| Storage | 20 GiB gp3 |

Then **Elastic IPs → Allocate → Associate** it with the instance, so the
address doesn't change when the server restarts. Write the IP down.

## 2. Connect and install Docker

From PowerShell on your PC (in the folder where the `.pem` file is):

```powershell
icacls dangote-key.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i dangote-key.pem ec2-user@YOUR_ELASTIC_IP
```

On the server:

```bash
sudo dnf install -y git
git clone -b production-pipeline https://github.com/Teninlanimi/Dangote-Refinery-ROI-Predictor.git
cd Dangote-Refinery-ROI-Predictor
bash deploy/ec2-setup.sh
exit          # log out so the docker group takes effect
```

## 3. Configure and start

SSH back in, then:

```bash
cd Dangote-Refinery-ROI-Predictor
cp .env.example .env
openssl rand -hex 16        # copy this as the database password
nano .env                   # set POSTGRES_PASSWORD and FRED_API_KEY; save with Ctrl+O, Enter, Ctrl+X
docker compose up -d --build
```

The first build takes a few minutes. Then check:

```bash
docker compose ps                     # db, web, scheduler, caddy all "running"/"healthy"
docker compose logs scheduler         # first run: Brent backfilled from Jan 2026, FX added
curl http://localhost/health          # {"status": "ok", "database": "ok", ...}
```

Open `http://YOUR_ELASTIC_IP` in your browser. The live data panel should
show Brent, USD/NGN and the crude factor. `http://YOUR_ELASTIC_IP/status`
shows every pipeline run and data check.

## 4. Turn on HTTPS (5 min)

No domain needed: `sslip.io` turns your IP into a hostname.

```bash
nano .env      # DOMAIN=YOUR.ELASTIC.IP.sslip.io   e.g. DOMAIN=3.85.12.34.sslip.io
docker compose up -d
docker compose logs caddy   # look for "certificate obtained successfully"
```

Now use `https://3.85.12.34.sslip.io`. If you buy a domain later, point an
A record at the Elastic IP and put that domain in `DOMAIN` instead.

## 5. Day-to-day

| Task | Command (on the server, in the project folder) |
|---|---|
| Deploy new code | `git pull && docker compose up -d --build` |
| Watch the pipeline | `docker compose logs -f scheduler` |
| Run the pipeline now | `docker compose exec web python -m pipeline.ingest` |
| Look at the data | `docker compose exec db psql -U roi -d roi -c "select series, observed_on, value, quality from market_observations order by observed_on desc limit 10;"` |
| Restart everything | `docker compose restart` |

**Backups:** `deploy/backup.sh` dumps the database nightly (instructions are
at the top of the file). To also copy dumps to S3, create a bucket, give the
instance an IAM role with `s3:PutObject` on it, and set `BACKUP_BUCKET` in `.env`.

## 6. Troubleshooting

- **Site doesn't load:** security group must allow port 80 (and 443) from
  `0.0.0.0/0`; `docker compose ps` should show caddy running.
- **Brent shows "—":** `FRED_API_KEY` missing or wrong; `/status` shows a
  `fetch` fail with the reason. Fix `.env`, then `docker compose up -d`.
- **Crack spread shows "—":** it needs Brent, petrol and diesel prices on the
  same day; check `/status` for a failed `gasoline_nyh` or `diesel_nyh` fetch.
- **Crude factor shows "—":** needs at least 60 days of H1 2026 Brent history,
  which the first successful Brent run backfills automatically.
- **`/health` says degraded:** no successful run in 36 hours. Check scheduler logs.
- **Server is slow / build killed:** the swap file from `ec2-setup.sh` helps; if
  it still struggles, stop the instance and change the type to `t3.small`.

## 7. Stopping costs

Stopping the instance stops compute charges, but the disk and Elastic IP still
bill a little. To remove everything: terminate the instance, then **release the
Elastic IP** (an unattached Elastic IP is still charged).

## Where to take it next

- **Amazon RDS** for the database (managed backups, failover): create a
  PostgreSQL instance in the same VPC, allow the EC2 security group on 5432,
  set `DATABASE_URL` in `.env`, remove the `db` service.
- **Automatic deploys:** a GitHub Actions job that SSHes in and runs
  `git pull && docker compose up -d --build` after CI passes on `main`.
- **CloudWatch alarms** on `/health` via Route 53 health checks.
