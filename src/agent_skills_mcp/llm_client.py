"""LLM client for executing skills using LangChain."""

import logging
import time

from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import SkillExecutionResult

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for executing skills via LLM providers using LangChain."""

    def __init__(self, default_model: str | None = None):
        """Initialize the LLM client.

        Args:
            default_model: Default model to use. If None, uses config default.
        """
        self.config = get_config()
        self.default_model = default_model or self.config.default_model

    def _create_llm(self, model_string: str):
        """Create LangChain LLM instance based on provider prefix.

        Args:
            model_string: Model string with provider prefix (e.g., "anthropic/claude-3-5-sonnet").

        Returns:
            LangChain LLM instance.

        Raises:
            ValueError: If provider is unsupported or model format is invalid.
        """
        if "/" not in model_string:
            raise ValueError(
                f"Invalid model format: {model_string}. "
                "Expected format: <provider>/<model-name>"
            )

        provider, model_name = model_string.split("/", 1)

        if provider == "anthropic":
            return ChatAnthropic(
                model=model_name,
                api_key=self.config.anthropic_api_key,
                max_tokens=8192,
            )
        elif provider == "bedrock":
            return ChatBedrock(
                model_id=model_name,
                region_name=self.config.aws_region_name,
                credentials_profile_name=None,  # Use environment variables
            )
        elif provider == "vertex_ai":
            return ChatVertexAI(
                model=model_name,
                project=self.config.vertexai_project,
                location=self.config.vertexai_location,
                max_tokens=8192,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def execute_with_skill(
        self,
        skill_name: str,
        skill_content: str,
        user_prompt: str,
        model: str | None = None,
        max_iterations: int = 10,
    ) -> SkillExecutionResult:
        """Execute a skill by injecting it as system prompt to the LLM.

        This implementation uses LangChain to handle the agent loop,
        including tool calling and iterative execution.

        Args:
            skill_name: Name of the skill being executed.
            skill_content: Complete skill content (SKILL.md) to use as system prompt.
            user_prompt: User's prompt/request.
            model: Model to use for execution. If None, uses default model.
            max_iterations: Maximum number of agent loop iterations.

        Returns:
            SkillExecutionResult with response, model info, and usage statistics.

        Raises:
            ValueError: If model credentials are not configured.
            Exception: If LLM API call fails.
        """
        selected_model = model or self.default_model

        # Validate model configuration
        self.config.validate_llm_config(selected_model)

        # Create LLM instance
        llm = self._create_llm(selected_model)

        # Prepare messages with skill as system prompt
        messages = [
            SystemMessage(content=skill_content),
            HumanMessage(content=user_prompt),
        ]

        # Log skill execution details
        logger.info("=" * 80)
        logger.info(f"Executing skill: {skill_name}")
        logger.info(f"Model: {selected_model}")
        logger.info("-" * 80)
        logger.info("System prompt (skill content, first 500 chars):")
        logger.info(skill_content[:500] + ("..." if len(skill_content) > 500 else ""))
        logger.info("-" * 80)
        logger.info("User prompt:")
        logger.info(user_prompt)
        logger.info("-" * 80)

        # Execute LLM call with timing
        start_time = time.time()
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            # TODO: Implement agent loop with tool calling
            # For now, we do a simple single-turn call
            # This will be enhanced to support <use_mcp_tool> parsing and iteration

            response = await llm.ainvoke(messages)
            response_content = response.content

            # Extract token usage
            if hasattr(response, "response_metadata") and response.response_metadata:
                usage = response.response_metadata.get("usage", {})
                total_input_tokens = usage.get("input_tokens", 0)
                total_output_tokens = usage.get("output_tokens", 0)

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
