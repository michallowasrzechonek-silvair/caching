# ETag Caching for Microservices

This is a simple demo of using ETag based cache in microservice-based application.

Make sure you are connected to Silvair's VPN, then type `docker-compose up`.

API is exposed by `bff` on `http://localhost:8080`.

## Parts

### Databases

All databases are hosted in the same PostgreSQL cluster, but are otherwise
independent.

### Internal REST

There are 2 backend services - `projects` and `commissioning`, each using its
own database (exclusively) and exposing a REST API.

Each backend service manages its own database using
[Alembic](https://alembic.sqlalchemy.org/en/latest/). Schema is upgraded to the
newest available revision before service starts.

### External REST

A third service is an [API
Gateway](https://microservices.io/patterns/apigateway.html) - `bff`. [^1]

It doesn't use any persistent database, only routes requests coming from
external clients to either `projects` or `commissioning`, or maybe even both of
them.

For simplicity, we don't use any authentication.

[^1]: Even though the name suggests a [Backend for
  Frontend](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends),
  this not true, as the service provides an uniform API for many different clients.

## Operation

### Data paths

Requests from external clients (e.g. your CLI) are always routed to `bff`
first, and only `bff` can access `projects` and `commissioning`.

According to principles outlined in
[Avoiding Micro-monoliths](https://slides.com/khorne/micro-monolith), both
backend services don't know about each other - the only client talking to
either or them if the `bff`.

### Purity

This means that for each backend service, content provided by all its endpoints depends
only on two things:
 - content of the database
 - content of the request

Furthermore, content of the database can change only through given backend service's API.

This means that we can easily implement
[ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag) based
caching between each of the backend services and the `bff`, even if the
external client doesn't use it.

Such a cache allows us to avoid querying databases when their content hasn't been
modified.
