# API contract

This document describes a future endpoint only. The endpoint is not implemented
in this milestone.

## Create a post

### Request

`POST /posts`

Request body:

```json
{
  "user_id": 1,
  "content": "Hello from InstaKill"
}
```

The client must provide a positive integer `user_id` for an existing user and a
non-blank string `content`. Whitespace around meaningful content is allowed and
is preserved by the application service.

### Successful response

Status: `201 Created`

```json
{
  "id": 42,
  "user_id": 1,
  "content": "Hello from InstaKill",
  "created_at": "2026-10-19T16:45:35Z"
}
```

`id` and `created_at` are assigned by the persistence boundary. The application
service currently returns a domain `Post` value without writing to SQLite.

### Validation and error cases

- `400 Bad Request`: malformed JSON or a request body with the wrong field
  types.
- `422 Unprocessable Entity`: `user_id` is missing, not a positive integer, or
  `content` is missing, not a string, or contains only whitespace.
- `404 Not Found`: no user exists for the supplied `user_id`.
- `500 Internal Server Error`: an unexpected persistence failure. The response
  must not expose database details.
