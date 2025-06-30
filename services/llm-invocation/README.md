# LLM Invocation Service

This service contains a simple Lambda function that forwards requests to
LLM backends such as Amazon Bedrock or a local Ollama instance.

Dependencies like `httpx` are listed in `requirements.txt`. When the stack
is built with AWS SAM the function package is created from this file. The
provided `llm-invocation-layer` includes the same dependencies so
`InvokeLLMLambda` works out of the box when deployed.
