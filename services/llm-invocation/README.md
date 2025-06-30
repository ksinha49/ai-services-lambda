# LLM Invocation Service

This service contains a simple Lambda function that forwards requests to
LLM backends such as Amazon Bedrock or a local Ollama instance.

All Python dependencies are provided by the shared
`common/layers/llm-invocation-layer` so no service specific
`requirements.txt` file is needed. The Lambda will work out of the box when
deployed with this layer.

The request payload must include a ``backend`` and ``prompt`` field.  An
optional ``system_prompt`` can also be supplied.  When present, this value is
forwarded as a system message for Bedrock backends or as the ``system`` field
for Ollama.
