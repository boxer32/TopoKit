"""Unit tests for Evaluation Harness."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from topokit.core.evaluation import (
    EvaluationHarness,
    SemanticSimilarityEvaluator,
    FactualConsistencyEvaluator,
    CoherenceEvaluator,
    PassAtKEvaluator,
    DriftDetectionEvaluator,
    MetricType,
)


class TestSemanticSimilarityEvaluator:
    """Test cases for Semantic Similarity Evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create semantic similarity evaluator."""
        return SemanticSimilarityEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_similarity(self, evaluator):
        """Test evaluating semantic similarity."""
        reference = "The cat sat on the mat"
        candidate = "A feline sat on the rug"
        
        result = await evaluator.evaluate(reference, candidate)
        
        assert result is not None
        assert "similarity" in result or "score" in result
        assert 0 <= result.get("similarity", result.get("score", 0)) <= 1
    
    @pytest.mark.asyncio
    async def test_evaluate_identical_texts(self, evaluator):
        """Test evaluating identical texts."""
        text = "The cat sat on the mat"
        
        result = await evaluator.evaluate(text, text)
        
        assert result is not None
        similarity = result.get("similarity", result.get("score", 0))
        assert similarity >= 0.9  # Should be very similar


class TestFactualConsistencyEvaluator:
    """Test cases for Factual Consistency Evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create factual consistency evaluator."""
        return FactualConsistencyEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_consistency(self, evaluator):
        """Test evaluating factual consistency."""
        retrieved_context = ["Paris is the capital of France"]
        generated_answer = "The capital of France is Paris"
        
        result = await evaluator.evaluate(retrieved_context, generated_answer)
        
        assert result is not None
        assert "consistent" in result or "score" in result


class TestCoherenceEvaluator:
    """Test cases for Coherence Evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create coherence evaluator."""
        return CoherenceEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_coherence(self, evaluator):
        """Test evaluating coherence."""
        text = "The cat sat on the mat. It was a sunny day. The mat was soft."
        
        result = await evaluator.evaluate(text)
        
        assert result is not None
        assert "coherence" in result or "score" in result


class TestPassAtKEvaluator:
    """Test cases for Pass At K Evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create pass at k evaluator."""
        return PassAtKEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_pass_at_k(self, evaluator):
        """Test evaluating pass@k."""
        candidates = [
            {"answer": "Answer 1", "valid": True},
            {"answer": "Answer 2", "valid": False},
            {"answer": "Answer 3", "valid": True},
        ]
        
        result = await evaluator.evaluate(candidates, k=2)
        
        assert result is not None
        assert "pass_at_k" in result or "score" in result


class TestDriftDetectionEvaluator:
    """Test cases for Drift Detection Evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create drift detection evaluator."""
        return DriftDetectionEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_drift(self, evaluator):
        """Test evaluating drift."""
        current_metric = 0.85
        baseline_metric = 0.90
        
        result = await evaluator.evaluate(current_metric, baseline_metric, threshold=0.10)
        
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2  # (score, details)


class TestEvaluationHarness:
    """Test cases for Evaluation Harness."""
    
    @pytest.fixture
    def harness(self):
        """Create evaluation harness."""
        return EvaluationHarness()
    
    @pytest.mark.asyncio
    async def test_evaluate_all(self, harness):
        """Test evaluating all metrics."""
        execution_result = {
            "output": "The cat sat on the mat",
            "latency_ms": 150,
            "tokens_used": 100,
        }
        expected_output = {
            "output": "A feline sat on the rug",
        }
        
        result = await harness.evaluate_all(
            execution_result,
            expected_output=expected_output,
        )
        
        assert result is not None
        assert hasattr(result, "metrics") or isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

