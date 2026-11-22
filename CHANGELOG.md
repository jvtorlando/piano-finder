# Changelog

All notable changes to Piano Finder are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- redesigned Django Admin with Unfold, using the Piano Finder gold palette, a moderation dashboard with counters and review queues, sidebar shortcuts with pending badges, status labels, photo thumbnails, tabbed piano forms with inline comments, and a one-click "approve and publish" action;
- public pages rebuilt on a shared `base.html` with Tailwind CSS v4 (via `django-tailwind-cli`), keeping the black, ivory and gold identity: consistent 16:10 cards, native swipe carousels, an accessible filter dialog with removable filter chips, catalog totals, toast messages, and page scripts moved to static files;
- HTMX (vendored, no CDN): catalog filters update the results in place as options are picked, with clean shareable URLs, and comments are submitted without a page reload;
- interactive map page (`/mapa/`) built with Leaflet and OpenStreetMap tiles, with a "near me" button that sorts pianos by distance using the browser's location, plus a location map on each piano page;
- latitude and longitude for pianos, filled automatically from the address through OpenStreetMap Nominatim when an administrator saves a piano, with a bulk "find coordinates" admin action and manual correction;
- Vercel Web Analytics and Speed Insights on Vercel deployments (cookieless, toggled with `VERCEL_ANALYTICS`);
- `carregar_exemplos` management command that seeds sample pianos and comments into the local development database.

### Changed

- "old money" visual direction: Cormorant Garamond and EB Garamond, antique gold, square corners, hairline rules and ornaments; outlined buttons instead of solid yellow blocks;
- catalog cards are edge to edge again, without borders, the "working" check mark or the catalog totals line; only pianos under maintenance get a note;
- piano type icons redrawn as fine line drawings of real pianos (upright, grand, digital on a stand, hybrid, grand seen from above);
- the suggestion form offers the four piano types directly instead of a two-step choice;
- site copy and README rewritten in plainer language;
- Brazilian states and piano types now have a single source of truth in `pianos/models.py`;
- the "how to get there" link uses an encoded Google Maps search URL.

### Fixed

- star rating: after voting the stars jumped back to the old average, the stars showed the visitor's vote while the number showed the average, there were no partial stars, and the number switched from "5,0" to "3.5" after a vote;
- static JS and CSS URLs now carry the deploy version (`?v=`), so browsers stop using old cached scripts after a release;
- local setup failing with an unconfigured database when `.env` contains an empty `DATABASE_URL`, as copied from `.env.example`; an empty value now falls back to SQLite.

## [1.0.0] - 2026-08-06

First formal public release of Piano Finder as a production application and portfolio project.

### Added

- public catalog of approved pianos with state, city, and piano-type filters;
- detailed piano pages with address, availability, Google Maps access, comments, votes, and star ratings;
- moderated community submissions supporting up to three photos;
- Django Admin workflow for reviewing pianos, comments, and uploaded images;
- PostgreSQL persistence on Neon, Cloudinary image delivery, Vercel deployment, and Hostinger-managed custom DNS;
- responsive 16:10 image editor for the public form and Django Admin, with drag, zoom, keyboard, and touch controls;
- automated Django test suite and GitHub Actions continuous integration;
- portfolio documentation, architecture notes, screenshots, and community validation metrics.

### Changed

- normalized edited photos to 1600×1000 JPEG output for consistent presentation;
- made catalog and detail images fill their mobile 16:10 frames edge to edge while preserving the existing tablet and desktop layouts;
- moved production data and uploaded media away from ephemeral serverless storage;
- established a pull-request-based workflow for changes to `main`.

### Fixed

- excessive mobile image zoom and inconsistent framing across source photo orientations;
- blank image rendering on affected iOS previews;
- Django Admin Cloudinary upload failures that returned HTTP 500;
- production migration ordering and Vercel static-asset deployment issues.

### Security

- restricted accepted image URLs to HTTPS resources from the configured Cloudinary account;
- added file-size, image-content, and server-side Admin upload validation;
- hardened production settings for HTTPS, secure cookies, HSTS, CSRF, framing, and MIME sniffing;
- added request limits to submissions, comments, votes, and ratings;
- excluded environment files, local databases, database backups, private keys, virtual environments, caches, logs, media, and deployment metadata from Git.

[Unreleased]: https://github.com/jvtorlando/piano-finder/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/jvtorlando/piano-finder/releases/tag/v1.0.0
