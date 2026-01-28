"""LLM client for executing skills using Strands Agents and LiteLLM."""

import asyncio
import logging
import time

from strands import Agent
from strands.models.litellm import LiteLLMModel

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import SkillExecutionResult
from agent_skills_mcp.tools import file_read, file_write, shell, web_fetch

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for executing skills via LLM providers using Strands Agents."""

    def __init__(self, default_model: str | None = None):
        """Initialize the LLM client.

        Args:
            default_model: Default model to use. If None, uses config default.
        """
        self.config = get_config()
        self.default_model = default_model or self.config.default_model

    def _create_llm_model(self, model_string: str) -> LiteLLMModel:
        """Create LiteLLM model instance based on provider prefix.

        Args:
            model_string: Model string with provider prefix (e.g., "anthropic/claude-3-5-sonnet").

        Returns:
            LiteLLMModel instance.

        Raises:
            ValueError: If provider is unsupported or model format is invalid.
        """
        if "/" not in model_string:
            raise ValueError(
                f"Invalid model format: {model_string}. "
                "Expected format: <provider>/<model-name>"
            )

        provider, model_name = model_string.split("/", 1)

        client_args = {}
        params = {"max_tokens": 8192}

        if provider == "anthropic":
            client_args["api_key"] = self.config.anthropic_api_key
        elif provider == "bedrock":
            client_args["aws_region_name"] = self.config.aws_region_name
        elif provider == "vertex_ai":
            client_args["vertex_project"] = self.config.vertexai_project
            client_args["vertex_location"] = self.config.vertexai_location
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return LiteLLMModel(
            client_args=client_args,
            model_id=model_string,
            params=params,
        )

    async def execute_with_skill(
        self,
        skill_name: str,
        skill_content: str,
        user_prompt: str,
    ) -> SkillExecutionResult:
        """Execute a skill by injecting it as system prompt to the LLM.

        This implementation uses Strands Agents to handle the agent loop,
        including tool calling and iterative execution.

        Args:
            skill_name: Name of the skill being executed.
            skill_content: Complete skill content (SKILL.md) to use as system prompt.
            user_prompt: User's prompt/request.

        Returns:
            SkillExecutionResult with response, model info, and usage statistics.

        Raises:
            ValueError: If model credentials are not configured.
            Exception: If LLM API call fails.
        """
        # Use default model from config
        selected_model = self.default_model

        # Validate model configuration
        self.config.validate_llm_config(selected_model)

        # Create LiteLLM model
        llm_model = self._create_llm_model(selected_model)

        # Create Strands Agent with skill content as system prompt
        agent = Agent(
            model=llm_model,
            system_prompt=skill_content,
            tools=[file_read, file_write, shell, web_fetch],
        )

        # Log skill execution details
        logger.info("=" * 80)
        logger.info(f"Executing skill: {skill_name}")
        logger.info(f"Model: {selected_model}")
        logger.info("-" * 80)

        # Execute agent with timing
        start_time = time.time()
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            # Run agent in a thread to avoid blocking
            result = await asyncio.to_thread(agent, user_prompt)

            # Extract response content
            if hasattr(result, "message"):
                message = result.message
                # Handle dict format: {'role': 'assistant', 'content': [{'text': '...'}]}
                if isinstance(message, dict):
                    content = message.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        # Extract text from first content block
                        response_content = content[0].get("text", str(message))
                    else:
                        response_content = str(message)
                else:
                    response_content = str(message)
            else:
                response_content = str(result)

            # Extract token usage
            if hasattr(result, "metrics") and result.metrics:
                # Try to get accumulated_usage
                usage = getattr(result.metrics, "accumulated_usage", None)
                if usage and isinstance(usage, dict):
                    total_input_tokens = usage.get("input_tokens", 0)
                    total_output_tokens = usage.get("output_tokens", 0)
                else:
                    # Log for debugging
                    logger.debug(f"No token usage found. Metrics: {result.metrics}")

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            logger.info("=" * 80)
            raise Exception(f"LLM API call failed: {e}") from e

        execution_time = time.time() - start_time

        # Log response details
        logger.info("LLM Response:")
        logger.info(response_content)
        logger.info("-" * 80)
        logger.info(
            f"Execution completed: {execution_time:.2f}s | "
            f"Input tokens: {total_input_tokens} | "
            f"Output tokens: {total_output_tokens}"
        )
        logger.info("=" * 80)

        return SkillExecutionResult(
            skill_name=skill_name,
            response=response_content,
            model=selected_model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            execution_time=execution_time,
        )
