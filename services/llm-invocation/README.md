# LLM Invocation Service

This service contains a simple Lambda function that forwards requests to
LLM backends such as Amazon Bedrock or a local Ollama instance.

All Python dependencies are provided by the shared
`common/layers/llm-invocation-layer` so no service specific
`requirements.txt` file is needed. The Lambda will work out of the box when
deployed with this layer.
