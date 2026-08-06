# Piano Finder

**A community-driven platform for mapping, documenting and locating publicly accessible pianos in São Paulo.**

Piano Finder is a web application developed with Python and Django to centralize information about public pianos and allow the community to contribute new locations.

---

## How the project started

The idea came from a personal interest in playing the piano.

I wanted to find an acoustic piano available for public use in São Paulo, but there was very little reliable information online. Most of what I found was concentrated on an outdated website, with limited details about whether the instruments were still available, accessible or in good condition.

Because of this difficulty, I began searching for public pianos around the city and documenting the process through a TikTok account.

The content quickly attracted attention, with some videos surpassing **80,000 views in a short period**.

People started interacting with the project, sharing their experiences and suggesting additional places where public pianos could potentially be found.

However, many of those recommendations were far from my location or difficult for me to visit personally. This created a limitation: the initiative depended on one person to travel, verify the information and publish each new location.

That experience revealed the need for a collaborative solution.

Instead of keeping the information centralized around one TikTok account, I decided to build a platform where users could register, document and share public piano locations themselves.

---

## The problem

Information about publicly accessible pianos in São Paulo was:

- difficult to find;
- scattered across different websites and social media posts;
- frequently incomplete or outdated;
- dependent on individual reports;
- difficult for one person to verify across the entire city.

Musicians and people interested in playing the piano did not have a centralized and collaborative source of information.

---

## The solution

Piano Finder was created to decentralize this information.

The platform allows the community to contribute public piano locations and helps users discover instruments available across São Paulo.

Its purpose is to:

- map publicly accessible pianos;
- document information about each location;
- make cultural spaces easier to discover;
- allow users to contribute new locations;
- centralize information that was previously scattered;
- create a database that can grow through community participation.

---

## Community interest

The project began on TikTok before becoming a web application.

Some of the videos documenting the search for public pianos surpassed **50,000 views**, and users began sending suggestions for new locations.

This engagement provided an early indication that other people were also interested in discovering, playing and documenting public pianos.

The website was developed as a response to that community participation and to the practical limitation of depending on a single person to visit every suggested location.

---

## Main features

- Registration of public piano locations
- Community-submitted information
- Centralized catalog of pianos
- Location and piano documentation
- Image and media management
- Collaborative expansion of the database
- Responsive web interface

---

## Technologies

### Application

- Python
- Django

### Database

- PostgreSQL (Neon) in production
- SQLite for local development when `DATABASE_URL` is not configured

### Media storage

- Cloudinary API

### Development practices

- Environment variables
- API credential protection
- Git and GitHub
- Django migrations
- Modular web application structure

---

## Media management

Cloudinary was integrated into the application to store and manage uploaded images.

Using an external media storage service avoids depending only on local application storage and provides a more appropriate structure for handling community-submitted media.

---

## Security

Sensitive information, such as API credentials and application configuration, is managed through environment variables.

Credentials are not written directly into the source code, reducing the risk of exposing private keys in the public repository.

The local environment configuration file is excluded from version control through `.gitignore`.

---

## Running the project locally

### 1. Clone the repository

```bash
git clone https://github.com/jvtorlando/piano-finder.git
cd piano-finder
