# Changelog

All notable changes to Piano Finder are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- redesigned Django Admin with Unfold, using the Piano Finder gold palette, a moderation dashboard with counters and review queues, sidebar shortcuts with pending badges, status labels, photo thumbnails, tabbed piano forms with inline comments, and a one-click "approve and publish" action;
- `carregar_exemplos` management command that seeds sample pianos and comments into the local development database.

### Fixed

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
