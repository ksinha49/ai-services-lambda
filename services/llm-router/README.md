# LLM Router Service

This service routes user prompts to different Large Language Model (LLM)
back‑ends.  It acts as a thin gateway in front of other services such as
Amazon Bedrock or a locally hosted Ollama instance.

``router-lambda/app.py`` implements the Lambda function entry point.  The
logic is split into small modules which can be reused outside of the
Lambda.  The modules are:

- **main_router.py** – exposes ``route_event`` which orchestrates the
  routing flow.
- **cascading_router.py** – implements a *weak then strong* routing
  pattern. It first calls a cheaper Bedrock model and only escalates to
  a stronger model when the weak response fails a quality check.
- **heuristic_router.py** – simple rule based routing using prompt
  length.
- **predictive_router.py** – placeholder for ML based routing logic.
- **generative_router.py** – fallback that always selects a backend so a
  response is returned.
- **routellm_integration.py** – helper for forwarding a request to an
  external RouteLLM service.

## Environment variables

The router depends on a few environment variables which can be provided
easily through AWS Parameter Store or the Lambda console:

- ``BEDROCK_OPENAI_ENDPOINTS`` – comma-separated Bedrock OpenAI‑compatible
  endpoints.
- ``BEDROCK_API_KEY`` – API key used when calling Bedrock.
- ``BEDROCK_TEMPERATURE`` – sampling temperature for Bedrock models (default ``0.5``).
- ``BEDROCK_NUM_CTX`` – context length for Bedrock calls (default ``4096``).
- ``BEDROCK_MAX_TOKENS`` – maximum tokens to generate (default ``2048``).
- ``BEDROCK_TOP_P`` – nucleus sampling parameter (default ``0.9``).
- ``BEDROCK_TOP_K`` – top‑k sampling parameter (default ``50``).
- ``BEDROCK_MAX_TOKENS_TO_SAMPLE`` – maximum tokens Bedrock should sample (default ``2048``).
- ``OLLAMA_ENDPOINTS`` – comma-separated URLs of the local Ollama services.
- ``OLLAMA_DEFAULT_MODEL`` – model name passed to Ollama when not
  supplied in the payload.
- ``PROMPT_COMPLEXITY_THRESHOLD`` – word count used by the heuristic
  router to decide when to switch from Ollama to Bedrock. When not set,
  the router defaults to a threshold of ``20`` words.
- ``ROUTELLM_ENDPOINT`` – optional URL for an external RouteLLM router.
- ``STRONG_MODEL_ID`` – identifier for the more capable Bedrock model.
- ``WEAK_MODEL_ID`` – identifier for the lightweight model used for short prompts.
- ``LLM_INVOCATION_FUNCTION`` – name of the Lambda function that actually
  calls the selected LLM backend.

## Deployment

The router can be deployed with SAM like the other services in this
repository.  Assuming the variables above are stored in Parameter Store,
you can deploy the Lambda with:

```bash
sam deploy \
  --template-file services/llm-router/template.yaml \
  --stack-name llm-router
```

(If ``template.yaml`` does not yet exist, copy one of the other service
templates as a starting point.)

## Usage

The Lambda expects an OpenAI style payload.  Example invocation using the
AWS CLI:

```bash
aws lambda invoke \
  --function-name llm-router \
  --payload '{"prompt": "Tell me a joke"}' out.json
```

The response will include a ``backend`` field indicating which service
handled the request. You may pass ``backend`` in the payload to force
a particular destination (``bedrock`` or ``ollama``). When not
provided, the router falls back to the complexity-based heuristic.
An optional ``strategy`` field is accepted for future routing modes.

## Bedrock OpenAI API Usage

Calls to Bedrock are issued against its OpenAI‑compatible REST API using the
``httpx`` package. When ``backend`` resolves to ``bedrock``, the Lambda forwards
the payload directly to the configured endpoint:

```python
import httpx

response = httpx.post(
    os.environ["BEDROCK_OPENAI_ENDPOINTS"].split(",")[0],
    headers={"Authorization": f"Bearer {os.environ.get('BEDROCK_API_KEY', '')}"},
    json={"model": os.environ["STRONG_MODEL_ID"], "prompt": prompt},
)
```
Model identifiers are provided by ``STRONG_MODEL_ID`` and ``WEAK_MODEL_ID``.
