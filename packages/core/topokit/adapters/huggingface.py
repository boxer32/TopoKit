"""
Module: huggingface_adapter
Purpose: Hugging Face adapter with model support
Inputs: Execution context, execution profile, prompt/data
Outputs: Execution results with model output
Dependencies: transformers library, adapter.framework
Failure Modes: Model loading failure → error, inference failure → retry
Trace: page:adapters, build:20250127, spec-id:T098
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

from .framework import (
    BaseAdapter,
    AdapterType,
    AdapterConfig,
    ExecutionContext,
    ExecutionResult,
    register_adapter,
)


logger = logging.getLogger(__name__)


class HuggingFaceAdapter(BaseAdapter):
    """Hugging Face adapter for local model inference."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize Hugging Face adapter."""
        super().__init__(config)
        self._pipeline = None
        self._tokenizer = None
        self._model = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.LLM_PROVIDER
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "huggingface"
    
    async def _initialize_impl(self) -> None:
        """Initialize Hugging Face model."""
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "Transformers library not installed. Install with: pip install transformers torch"
            )
        
        # Get model configuration
        model_name = self.config.connection_params.get(
            "model_name",
            "gpt2"  # Default lightweight model
        )
        
        task = self.config.connection_params.get("task", "text-generation")
        
        # Load model
        try:
            if task == "text-generation":
                self._tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._model = AutoModelForCausalLM.from_pretrained(model_name)
                self._model.to(self._device)
                
                # Create pipeline
                self._pipeline = pipeline(
                    task,
                    model=self._model,
                    tokenizer=self._tokenizer,
                    device=0 if self._device == "cuda" else -1,
                )
            else:
                # Use pipeline for other tasks
                self._pipeline = pipeline(
                    task,
                    model=model_name,
                    device=0 if self._device == "cuda" else -1,
                )
            
            logger.info(f"Hugging Face model {model_name} loaded on {self._device}")
        
        except Exception as e:
            raise RuntimeError(f"Failed to load Hugging Face model: {e}")
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute Hugging Face model inference."""
        if not self._pipeline:
            raise RuntimeError("Hugging Face model not initialized")
        
        # Extract input
        prompt = self._extract_prompt(context.input_data)
        
        # Prepare generation parameters
        generation_kwargs = {
            "max_length": execution_profile.max_tokens,
            "temperature": execution_profile.temperature,
            "top_p": execution_profile.top_p,
            "do_sample": execution_profile.temperature > 0,
        }
        
        # Add seed if available
        if execution_profile.seed:
            try:
                import torch
                if isinstance(execution_profile.seed, int):
                    torch.manual_seed(execution_profile.seed)
                elif isinstance(execution_profile.seed, str):
                    # Use hash of seed string
                    torch.manual_seed(hash(execution_profile.seed) % (2**32))
            except Exception:
                pass
        
        # Run inference
        import asyncio
        
        try:
            # Run in thread pool to avoid blocking
            result = await asyncio.to_thread(
                self._pipeline,
                prompt,
                **generation_kwargs,
            )
            
            # Extract output
            if isinstance(result, list) and len(result) > 0:
                output_text = result[0].get("generated_text", str(result[0]))
            else:
                output_text = str(result)
            
            # Estimate tokens (rough approximation)
            tokens_used = len(prompt.split()) + len(output_text.split())
            
            return ExecutionResult(
                success=True,
                output_data={
                    "response": output_text,
                    "model": self.config.connection_params.get("model_name", "unknown"),
                },
                confidence=1.0,
                tokens_used=tokens_used,
                metadata={
                    "device": self._device,
                    "model": self.config.connection_params.get("model_name"),
                },
            )
        except Exception as e:
            logger.error(f"Hugging Face inference failed: {e}")
            raise
    
    async def _health_check_impl(self) -> bool:
        """Check Hugging Face model health."""
        if not self._pipeline:
            return False
        
        try:
            # Simple health check - run minimal inference
            test_prompt = "Hello"
            import asyncio
            
            await asyncio.to_thread(
                self._pipeline,
                test_prompt,
                max_length=10,
            )
            return True
        except Exception:
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup Hugging Face model."""
        if self._model:
            del self._model
        if self._tokenizer:
            del self._tokenizer
        if self._pipeline:
            del self._pipeline
        
        # Clear GPU memory
        if self._device == "cuda":
            import torch
            torch.cuda.empty_cache()
        
        self._pipeline = None
        self._tokenizer = None
        self._model = None
    
    def _extract_prompt(self, input_data: Any) -> str:
        """Extract prompt from input data."""
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("prompt") or input_data.get("message") or str(input_data)
        else:
            return str(input_data)


# Register adapter
if HUGGINGFACE_AVAILABLE:
    register_adapter("huggingface", HuggingFaceAdapter)

