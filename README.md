# CarHire

## AI vehicle search

The public `POST /api/assistant/search` endpoint uses the Anthropic API when
`ANTHROPIC_API_KEY` is configured. Set `ANTHROPIC_MODEL` to choose the model
(defaults to `claude-3-5-haiku-latest`). Without a key, or if the Anthropic
request fails, searches use basic matching against vehicle make, model, and
location. The endpoint is limited to 10 requests per minute per IP address.