"""LLM client for executing skills using LiteLLM."""

import time

from litellm import acompletion

from agent_skills_mcp.config import get_config
from agent_skills_mcp.models import SkillExecutionResult


class LLMClient:
    """Client for executing skills via LLM providers using LiteLLM."""

    def __init__(self, default_model: str | None = None):
        """Initialize the LLM client.

        Args:
            default_model: Default model to use. If None, uses config default.
        """
        self.config = get_config()
        self.default_model = default_model or self.config.default_model

    async def execute_with_skill(
        self,
        skill_name: str,
        skill_content: str,
        user_prompt: str,
        model: str | None = None,
    ) -> SkillExecutionResult:
        """Execute a skill by injecting it as system prompt to the LLM.

        Args:
            skill_name: Name of the skill being executed.
            skill_content: Complete skill content (SKILL.md) to use as system prompt.
            user_prompt: User's prompt/request.
            model: Model to use for execution. If None, uses default model.

        Returns:
            SkillExecutionResult with response, model info, and usage statistics.

        Raises:
            ValueError: If model credentials are not configured.
            Exception: If LLM API call fails.
        """
        selected_model = model or self.default_model

        # Validate model configuration
        self.config.validate_llm_config(selected_model)

        # Prepare messages
        messages = [
            {"role": "system", "content": skill_content},
            {"role": "user", "content": user_prompt},
        ]

        # Execute LLM call with timing
        start_time = time.time()

        try:
            response = await acompletion(
                model=selected_model,
                messages=messages,
            )
        except Exception as e:
            raise Exception(f"LLM API call failed: {e}") from e

        execution_time = time.time() - start_time

        # Extract response content
        response_content = response.choices[0].message.content

        # Extract usage statistics
        usage = response.usage if hasattr(response, "usage") else None
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None

        return SkillExecutionResult(
            skill_name=skill_name,
            response=response_content,
            model=selected_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            execution_time=execution_time,
        )
