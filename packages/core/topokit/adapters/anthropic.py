"""
Module: anthropic_adapter
Purpose: Anthropic adapter with Claude integration
Inputs: Execution context, execution profile, prompt/data
Outputs: Execution results with tokens, cost, and confidence
Dependencies: anthropic library, adapter.framework
Failure Modes: API failure → retry with exponential backoff, rate limit → circuit breaker
Trace: page:adapters, build:20250127, spec-id:T109
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .framework import (
    BaseAdapter,
    AdapterType,
    AdapterConfig,
    ExecutionContext,
    ExecutionResult,
    register_adapter,
)


logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseAdapter):
    """Anthropic adapter for Claude models."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize Anthropic adapter."""
        super().__init__(config)
        self._client: Optional[AsyncAnthropic] = None
        self._sync_client: Optional[Anthropic] = None
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.LLM_PROVIDER
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "anthropic"
    
    async def _initialize_impl(self) -> None:
        """Initialize Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic library not installed. Install with: pip install anthropic"
            )
        
        api_key = self.config.connection_params.get("api_key")
        if not api_key:
            raise ValueError("Anthropic API key required in connection_params")
        
        self._client = AsyncAnthropic(api_key=api_key)
        self._sync_client = Anthropic(api_key=api_key)
        
        # Test connection
        await self._health_check_impl()
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute Anthropic API call."""
        if not self._client:
            raise RuntimeError("Anthropic client not initialized")
        
        # Extract prompt from input data
        prompt = self._extract_prompt(context.input_data)
        model = self._get_model(context)
        
        # Build request parameters
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": execution_profile.temperature,
            "top_p": execution_profile.top_p,
            "max_tokens": execution_profile.max_tokens,
        }
        
        # Make API call
        response = await self._client.messages.create(**request_params)
        
        # Extract response
        output_text = response.content[0].text
        usage = response.usage
        
        # Calculate cost (approximate)
        cost_usd = self._calculate_cost(model, usage.input_tokens, usage.output_tokens)
        
        return ExecutionResult(
            success=True,
            output_data={
                "response": output_text,
                "model": model,
                "stop_reason": response.stop_reason,
            },
            confidence=1.0,
            tokens_used=usage.input_tokens + usage.output_tokens,
            cost_usd=cost_usd,
            metadata={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "model": model,
                "response_id": response.id,
            },
        )
    
    async def _health_check_impl(self) -> bool:
        """Check Anthropic API health."""
        if not self._client:
            return False
        
        try:
            # Simple health check - make minimal API call
            await self._client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup Anthropic client."""
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
        model = self.config.connection_params.get(
            "model",
            "claude-3-5-sonnet-20241022"
        )
        return model
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost in USD (approximate pricing)."""
        # Pricing as of 2024 (approximate)
        pricing = {
            "claude-3-5-sonnet-20241022": (0.003 / 1000, 0.015 / 1000),
            "claude-3-opus-20240229": (0.015 / 1000, 0.075 / 1000),
            "claude-3-sonnet-20240229": (0.003 / 1000, 0.015 / 1000),
            "claude-3-haiku-20240307": (0.00025 / 1000, 0.00125 / 1000),
        }
        
        input_price, output_price = pricing.get(model, (0.003 / 1000, 0.015 / 1000))
        
        cost = (input_tokens * input_price) + (output_tokens * output_price)
        return round(cost, 6)


# Register adapter
if ANTHROPIC_AVAILABLE:
    register_adapter("anthropic", AnthropicAdapter)

