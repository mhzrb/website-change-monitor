# Website Change Monitor

[![Tests](https://github.com/mhzrb/website-change-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/mhzrb/website-change-monitor/actions/workflows/ci.yml)

A Django-based monitoring service that tracks web pages for meaningful content
changes and sends email alerts when monitored content is updated.

The application uses Celery workers and Redis-backed task queues for background
checks, `django-celery-beat` for periodic scheduling, BeautifulSoup with optional
CSS selectors for targeted content extraction, and SHA-256 hashes for efficient
change detection.

## Screenshots

### Watched sites

![Watched sites list](screenshots/site-list.jpg)

### Change history

![Change history](screenshots/change-history.jpg)

## Engineering Highlights

- Django web application for managing monitored URLs and change history
- Celery worker processes for asynchronous page checks
- Redis-backed task queue separating web requests from background work
- Database-backed recurring schedules with `django-celery-beat`
- Per-site check frequencies with due-time filtering before task dispatch
- Optional CSS selectors to reduce false positives from noisy page content
- SHA-256 content hashing for efficient change detection
- Retry-safe, idempotent site-check tasks
- Email notifications and persistent change-event history
- Manual on-demand checks alongside scheduled monitoring

## Why I Built It

I originally built the project after repeatedly checking pages such as Dutch
immigration updates and company career pages for changes. The goal was to turn
that manual workflow into a small monitoring system while exploring the
engineering behind asynchronous background jobs, scheduling, retries, and
separating web requests from long-running work.

## Features

- Watch any URL and optionally scope monitoring to a CSS selector
- Choose a check frequency per site: 15 minutes, hourly, every 6 hours, or daily
- Run page checks asynchronously through Celery workers
- Detect changes by hashing extracted page content with SHA-256
- Send an email notification when monitored content changes
- Keep a persistent change-history log for each site
- Trigger an immediate check with a manual **Check now** action
- Inspect monitored sites and events through the Django admin interface

## How It Works

1. A user creates a `WatchedSite` with a URL, optional CSS selector, and check
   frequency.
2. Every 15 minutes, Celery Beat triggers `check_all_sites`.
3. The dispatcher evaluates each site's `check_frequency_minutes` and sends only
   due sites to the Celery queue.
4. A worker executes `check_site`, fetches the page, extracts the relevant text,
   and calculates a SHA-256 hash.
5. The new hash is compared with the previously stored value.
6. If the content changed, the application records a `ChangeEvent` and sends an
   email notification.

## Architecture

```text
                         ┌──────────────────┐
                         │   Django web UI  │
                         │   + admin        │
                         └────────┬─────────┘
                                  │
                                  v
                         ┌──────────────────┐
                         │ Application DB   │
                         │ sites + history  │
                         └──────────────────┘

Celery Beat
    │
    │ periodic dispatch
    v
check_all_sites
    │
    │ due-site tasks
    v
Redis broker ───────▶ Celery worker ───────▶ Target webpage
                           │                      │
                           │  extract + hash     │
                           ◀──────────────────────┘
                           │
                           ├──▶ ChangeEvent
                           └──▶ Email notification
```

The scheduler and workers are intentionally separate processes. Celery Beat
decides when checks should be dispatched, while Celery workers perform the
network and parsing work independently of the Django request cycle.

## Tech Stack

- Python 3.10+
- Django 4.2
- Celery 5
- Redis
- `django-celery-beat`
- BeautifulSoup4
- `requests`
- SQLite for local development
- Bootstrap 5

## Local Development

### Prerequisites

- Python 3.10+
- Redis

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable --now redis-server
redis-cli ping
```

`redis-cli ping` should return:

```text
PONG
```

### Setup

```bash
git clone https://github.com/<your-username>/website-change-monitor.git
cd website-change-monitor

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Set SECRET_KEY and any optional email settings in .env

python manage.py migrate
python manage.py createsuperuser
python manage.py setup_periodic_task
```

The superuser step is optional and is only needed for Django admin access.

### Run the application

Run the web application, worker, and scheduler as separate processes.

**Terminal 1 — Django web app**

```bash
python manage.py runserver
```

**Terminal 2 — Celery worker**

```bash
celery -A sitemonitor worker -l info
```

**Terminal 3 — Celery Beat scheduler**

```bash
celery -A sitemonitor beat -l info
```

Then open:

```text
http://localhost:8000
```

## Email Configuration

The default Django console email backend prints notifications to the terminal,
which makes local testing possible without an external email provider.

For real email delivery, configure SMTP credentials through environment
variables in `.env`. Credentials should never be committed to the repository.

## Project Structure

```text
sitemonitor/
  # Django project settings and Celery configuration

monitor/
  models.py
  # WatchedSite and ChangeEvent models

  tasks.py
  # Celery tasks: check_site and check_all_sites

  views.py
  # CRUD views for monitored sites

  management/commands/setup_periodic_task.py
  # Periodic schedule registration

  templates/monitor/
  # Bootstrap templates
```

## Design Trade-offs and Limitations

- Page checks use normal HTTP requests, so content that only appears after
  client-side JavaScript execution may not be visible to the monitor.
- Change detection is hash-based: it reliably identifies that monitored content
  changed, but it does not generate a semantic text diff.
- Dynamic elements such as timestamps, ads, or counters can create noisy
  changes; CSS selectors can narrow monitoring to the meaningful section.
- Scheduling uses a 15-minute dispatcher interval and then checks each site's
  configured frequency, so the system is designed for periodic monitoring
  rather than sub-minute alerts.
- SQLite is convenient for local development; a production deployment can use a
  production-grade database without changing the monitoring architecture.

## Quality Checks

Run the Django system check and test suite locally:

```bash
python manage.py check
python manage.py test monitor.tests -v 2
```

GitHub Actions runs the same validation on pushes to `main` and on pull
requests using Python 3.12.

## Deployment

A deployment needs separate long-running processes for:

- Django web application
- Celery worker
- Celery Beat scheduler
- Redis

The same repository can be deployed to a platform that supports multiple
process types and a managed or external Redis service.

## Security and Configuration

- Keep `SECRET_KEY`, SMTP credentials, and other secrets in environment variables
- Do not commit `.env`
- Treat monitored URLs and notification email addresses as application data
- Use production Django security settings when exposing the application publicly

## Future Improvements

- Show textual diffs instead of only recording that a page changed
- Add per-site pause/resume controls
- Add webhook or Telegram notifications alongside email
- Support JavaScript-rendered pages through an optional browser-based fetcher
- Add monitoring metrics for check duration, failures, and queue health
- Add configurable retry policies for transient network failures

## License

MIT
