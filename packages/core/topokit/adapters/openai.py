"""
Module: openai_adapter
Purpose: OpenAI adapter with full API support for GPT models
Inputs: Execution context, execution profile, prompt/data
Outputs: Execution results with tokens, cost, and confidence
Dependencies: openai library, adapter.framework
Failure Modes: API failure → retry with exponential backoff, rate limit → circuit breaker
Trace: page:adapters, build:20250127, spec-id:T108
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .framework import (
    BaseAdapter,
    AdapterType,
    AdapterConfig,
    ExecutionContext,
    ExecutionResult,
    register_adapter,
)


logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """OpenAI adapter for GPT models with full API support."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize OpenAI adapter."""
        super().__init__(config)
        self._client: Optional[AsyncOpenAI] = None
        self._sync_client: Optional[OpenAI] = None
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.LLM_PROVIDER
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "openai"
    
    async def _initialize_impl(self) -> None:
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai"
            )
        
        api_key = self.config.connection_params.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key required in connection_params")
        
        self._client = AsyncOpenAI(api_key=api_key)
        self._sync_client = OpenAI(api_key=api_key)
        
        # Test connection
        await self._health_check_impl()
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute OpenAI API call."""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Extract prompt from input data
        prompt = self._extract_prompt(context.input_data)
        model = self._get_model(context)
        
        # Build request parameters
        request_params = {
            "model": model,
            "messages": self._format_messages(prompt),
            "temperature": execution_profile.temperature,
            "top_p": execution_profile.top_p,
            "max_tokens": execution_profile.max_tokens,
        }
        
        # Add seed if available
        if execution_profile.seed:
            try:
                seed = int(execution_profile.seed)
                request_params["seed"] = seed
            except (ValueError, TypeError):
                pass
        
        # Make API call
        response = await self._client.chat.completions.create(**request_params)
        
        # Extract response
        output_text = response.choices[0].message.content
        usage = response.usage
        
        # Calculate cost (approximate)
        cost_usd = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
        
        return ExecutionResult(
            success=True,
            output_data={
                "response": output_text,
                "model": model,
                "finish_reason": response.choices[0].finish_reason,
            },
            confidence=1.0,
            tokens_used=usage.total_tokens,
            cost_usd=cost_usd,
            metadata={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "model": model,
                "response_id": response.id,
            },
        )
    
    async def _health_check_impl(self) -> bool:
        """Check OpenAI API health."""
        if not self._client:
            return False
        
        try:
            # Simple health check - list models
            await self._client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup OpenAI client."""
        if self._client:
            await self._client.close()
        self._client = None
        self._sync_client = None
    
    def _extract_prompt(self, input_data: Any) -> str:
        """Extract prompt from input data."""
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("prompt") or input_data.get("message") or str(input_data)
        else:
            return str(input_data)
    
    def _get_model(self, context: ExecutionContext) -> str:
        """Get model from context or config."""
        # Check node metadata
        if hasattr(context.node, 'metadata') and context.node.metadata:
            model = context.node.metadata.get("model")
            if model:
                return model
        
        # Check config
        model = self.config.connection_params.get("model", "gpt-4-turbo-preview")
        return model
    
    def _format_messages(self, prompt: str) -> list:
        """Format prompt as messages for chat API."""
        return [{"role": "user", "content": prompt}]
    
    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost in USD (approximate pricing)."""
        # Pricing as of 2024 (approximate)
        pricing = {
            "gpt-4-turbo-preview": (0.01 / 1000, 0.03 / 1000),
            "gpt-4": (0.03 / 1000, 0.06 / 1000),
            "gpt-3.5-turbo": (0.001 / 1000, 0.002 / 1000),
        }
        
        prompt_price, completion_price = pricing.get(model, (0.01 / 1000, 0.03 / 1000))
        
        cost = (prompt_tokens * prompt_price) + (completion_tokens * completion_price)
        return round(cost, 6)


# Register adapter
if OPENAI_AVAILABLE:
    register_adapter("openai", OpenAIAdapter)

