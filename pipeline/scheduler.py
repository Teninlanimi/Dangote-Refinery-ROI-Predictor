"""
Long-running scheduler: runs the pipeline once on start, then at the hours
listed in SCHEDULE_HOURS_UTC (default 06:00 and 18:00 UTC).

On AWS this is the "scheduler" service in docker-compose.yml - a separate
process from the web server, so gunicorn workers never run duplicate jobs.

Run locally:  py -m pipeline.scheduler   (Ctrl+C to stop)
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from pipeline import ingest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scheduler")


def job():
    try:
        result = ingest.run()
        log.info("run %s finished: %s, +%s rows", result["run_id"], result["status"],
                 result["rows_inserted"])
    except Exception:  # keep the scheduler alive whatever happens in one run
        log.exception("pipeline run crashed")


def main():
    hours = config.SCHEDULE_HOURS_UTC.replace(" ", "")
    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(job, CronTrigger(hour=hours, minute=5, timezone="UTC"),
                  id="ingest", max_instances=1, coalesce=True, misfire_grace_time=3600)
    log.info("scheduler started - pipeline runs at %s:05 UTC", hours)
    job()  # fill the database straight away on (re)start
    sched.start()


if __name__ == "__main__":
    main()
