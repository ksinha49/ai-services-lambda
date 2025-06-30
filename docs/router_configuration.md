# LLM Router Configuration

This document details the environment variables used by the router Lambda and how they are typically provided.

## Environment Variables

| Name | Description |
| ---- | ----------- |
| `BEDROCK_OPENAI_ENDPOINTS` | Comma‑separated Bedrock endpoints implementing the OpenAI API. |
| `BEDROCK_API_KEY` | API key to authenticate when calling Bedrock. |
| `OLLAMA_ENDPOINTS` | Comma‑separated URLs of the local Ollama services. |
| `OLLAMA_DEFAULT_MODEL` | Default model name if one is not supplied in the payload. |
| `PROMPT_COMPLEXITY_THRESHOLD` | Word count threshold that determines when to switch from Ollama to Bedrock (defaults to `20`). |
| `ROUTELLM_ENDPOINT` | Optional URL for forwarding requests to a RouteLLM service. |
| `STRONG_MODEL_ID` | Identifier for the more capable Bedrock model. |
| `WEAK_MODEL_ID` | Identifier for the lightweight model used with shorter prompts. |
| `LLM_INVOCATION_FUNCTION` | Name of the Lambda used for actual model invocation. |

## Setting Values with Parameter Store

1. Open AWS Systems Manager &rarr; Parameter Store.
2. Create parameters for each variable under your stack's prefix.
3. Deploy the Lambda with `sam deploy`, passing the prefix via `--parameter-overrides` if needed.
4. During execution the Lambda reads these values from the environment.
