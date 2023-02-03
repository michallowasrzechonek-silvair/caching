# ETag Caching for Microservices

This is a simple demo of using ETag based cache in microservice-based application.

Make sure you are connected to Silvair's VPN, then type `docker-compose up`.

API is exposed by `bff` on `http://localhost:8080`.

## Parts

### Databases

All databases are hosted in the same PostgreSQL cluster, but are otherwise
independent.

### Internal REST

There are 3 backend services - `projects`, `commissioning` and `reconf` each using its
own database (exclusively) and exposing a REST API.

Each backend service manages its own database using
[Alembic](https://alembic.sqlalchemy.org/en/latest/). Schema is upgraded to the
newest available revision before service starts.

### External REST

Another service is an [API
Gateway](https://microservices.io/patterns/apigateway.html) - `bff`. [^1]

It doesn't use any persistent database, only routes requests coming from
external clients to either `projects`, `commissioning` or `reconf`, or maybe even all of
them.

For simplicity, we don't use any authentication.

[^1]: Even though the name suggests a [Backend for
  Frontend](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends),
  this not true, as the service provides an uniform API for many different clients.

## Operation

### Data paths

Requests from external clients (e.g. your CLI) are always routed to `bff`
first, and only `bff` can access other services.

According to principles outlined in
[Avoiding Micro-monoliths](https://slides.com/khorne/micro-monolith), 
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

## Cache keys

Resources returned by internal services are cached in `bff`'s RAM, while services themselves keep only the
ETag value, in order to compare `If-None-Match` header provided by the `bff`, and send back a `304 Not
Modified` response without querying the database. Such a response has an empty body.

When sending back a real resource, services include an `ETag` header with hash of the generated JSON document,
and also a `Vary` header, informing `bff` which HTTP headers were used to construct the cache key.

## Caching requests with body

When sending a POST request, `bff` is supposed to send an additional `Content-Digest` [2] header,
informing the service about version of the input data. The server may then decide to include this header in
`Vary` resonse header, informing `bff` that response can be cached.

This makes it possible to cache results of operations that use externally provided data, e.g. calculating the
audit.

[^2]: https://httpwg.org/http-extensions/draft-ietf-httpbis-digest-headers.html#content-digest
