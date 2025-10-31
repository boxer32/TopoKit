"""
Module: langchain_adapter
Purpose: LangChain adapter with chain integration
Inputs: Execution context, execution profile, prompt/data
Outputs: Execution results with chain output
Dependencies: langchain library, adapter.framework
Failure Modes: Chain execution failure → retry, missing dependencies → error
Trace: page:adapters, build:20250127, spec-id:T096
"""

from typing import Any, Dict, Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import logging

if TYPE_CHECKING:
    from langchain.chains.base import Chain
    from langchain.schema import BaseRetriever, BaseLLM
    from langchain.callbacks.base import BaseCallbackHandler

try:
    from langchain.chains.base import Chain
    from langchain.schema import BaseRetriever, BaseLLM
    from langchain.callbacks.base import BaseCallbackHandler
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Type stubs for when langchain is not available
    Chain = Any
    BaseRetriever = Any
    BaseLLM = Any
    BaseCallbackHandler = Any

from .framework import (
    BaseAdapter,
    AdapterType,
    AdapterConfig,
    ExecutionContext,
    ExecutionResult,
    register_adapter,
)


logger = logging.getLogger(__name__)


class LangChainAdapter(BaseAdapter):
    """LangChain adapter for chain integration."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize LangChain adapter."""
        super().__init__(config)
        self._chain: Optional[Chain] = None
        self._llm: Optional[BaseLLM] = None
        self._retriever: Optional[BaseRetriever] = None
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.LLM_PROVIDER
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "langchain"
    
    async def _initialize_impl(self) -> None:
        """Initialize LangChain components."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain library not installed. Install with: pip install langchain"
            )
        
        # Initialize chain from config
        chain_config = self.config.connection_params.get("chain_config", {})
        
        # Build chain if provided
        if "chain_type" in chain_config:
            self._chain = self._build_chain(chain_config)
        else:
            # Build simple LLM chain
            self._llm = self._build_llm(chain_config)
            self._chain = self._build_default_chain(self._llm)
        
        # Initialize retriever if configured
        if "retriever_config" in chain_config:
            self._retriever = self._build_retriever(chain_config["retriever_config"])
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute LangChain chain."""
        if not self._chain:
            raise RuntimeError("LangChain chain not initialized")
        
        # Extract input
        input_data = self._prepare_input(context.input_data)
        
        # Execute chain
        # Note: LangChain chains are typically synchronous, so we run in executor
        import asyncio
        
        try:
            if hasattr(self._chain, 'ainvoke'):
                # Async chain execution
                result = await self._chain.ainvoke(input_data)
            else:
                # Sync chain execution - run in thread pool
                result = await asyncio.to_thread(self._chain.invoke, input_data)
            
            return ExecutionResult(
                success=True,
                output_data=result,
                confidence=1.0,
                metadata={
                    "chain_type": type(self._chain).__name__,
                    "has_retriever": self._retriever is not None,
                },
            )
        except Exception as e:
            logger.error(f"LangChain execution failed: {e}")
            raise
    
    async def _health_check_impl(self) -> bool:
        """Check LangChain health."""
        if not self._chain:
            return False
        
        try:
            # Simple health check
            test_input = {"query": "test"}
            if hasattr(self._chain, 'ainvoke'):
                await self._chain.ainvoke(test_input)
            else:
                import asyncio
                await asyncio.to_thread(self._chain.invoke, test_input)
            return True
        except Exception:
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup LangChain resources."""
        self._chain = None
        self._llm = None
        self._retriever = None
    
    def _prepare_input(self, input_data: Any) -> Dict[str, Any]:
        """Prepare input for LangChain chain."""
        if isinstance(input_data, dict):
            return input_data
        elif isinstance(input_data, str):
            return {"query": input_data, "input": input_data}
        else:
            return {"input": str(input_data)}
    
    def _build_chain(self, config: Dict[str, Any]) -> Chain:
        """Build chain from configuration."""
        chain_type = config.get("chain_type", "llm_chain")
        
        # Import chain types as needed
        try:
            from langchain.chains import LLMChain, RetrievalQA
        
            if chain_type == "llm_chain":
                llm = self._build_llm(config)
                prompt_template = config.get("prompt_template")
                if prompt_template:
                    from langchain.prompts import PromptTemplate
                    prompt = PromptTemplate.from_template(prompt_template)
                    return LLMChain(llm=llm, prompt=prompt)
                return LLMChain(llm=llm)
            
            elif chain_type == "retrieval_qa":
                llm = self._build_llm(config)
                retriever = self._build_retriever(config.get("retriever_config", {}))
                if retriever:
                    return RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
            
            else:
                raise ValueError(f"Unknown chain type: {chain_type}")
        
        except ImportError as e:
            raise ImportError(f"Required LangChain components not available: {e}")
    
    def _build_llm(self, config: Dict[str, Any]) -> BaseLLM:
        """Build LLM from configuration."""
        llm_type = config.get("llm_type", "openai")
        
        try:
            if llm_type == "openai":
                from langchain.llms import OpenAI
                return OpenAI(
                    temperature=config.get("temperature", 0.7),
                    max_tokens=config.get("max_tokens", 1000),
                )
            elif llm_type == "anthropic":
                from langchain.llms import Anthropic
                return Anthropic(
                    temperature=config.get("temperature", 0.7),
                    max_tokens_to_sample=config.get("max_tokens", 1000),
                )
            else:
                raise ValueError(f"Unknown LLM type: {llm_type}")
        
        except ImportError as e:
            raise ImportError(f"Required LLM library not available: {e}")
    
    def _build_default_chain(self, llm: BaseLLM) -> Chain:
        """Build default chain from LLM."""
        from langchain.chains import LLMChain
        return LLMChain(llm=llm)
    
    def _build_retriever(self, config: Dict[str, Any]) -> Optional[BaseRetriever]:
        """Build retriever from configuration."""
        # Placeholder - implement based on vector store configuration
        return None


# Register adapter
if LANGCHAIN_AVAILABLE:
    register_adapter("langchain", LangChainAdapter)

