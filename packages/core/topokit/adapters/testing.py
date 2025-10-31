"""
Module: adapter_testing
Purpose: Adapter testing framework with validation and performance benchmarks
Inputs: Adapter instances, test scenarios, performance targets
Outputs: Test results, validation reports, performance metrics
Dependencies: adapter.framework, pytest
Failure Modes: Test failure → detailed error reporting
Trace: page:adapters, build:20250127, spec-id:T102
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import time
import logging

from .framework import BaseAdapter, AdapterConfig, ExecutionContext, ExecutionResult
from ..types.topology import Node, NodeKind, ExecutionProfile
from ..core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class TestScenario:
    """Test scenario for adapter validation."""
    name: str
    description: str
    input_data: Any
    expected_output: Optional[Any] = None
    expected_pattern: Optional[str] = None
    max_latency_ms: float = 5000.0
    min_confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result from adapter test."""
    scenario_name: str
    passed: bool
    latency_ms: float
    confidence: float
    error: Optional[str] = None
    actual_output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBenchmark:
    """Performance benchmark results."""
    adapter_id: str
    test_name: str
    latency_ms: float
    throughput_rps: float
    tokens_per_second: Optional[float] = None
    cost_per_request: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdapterTester:
    """Testing framework for adapters."""
    
    def __init__(self):
        """Initialize adapter tester."""
        self.logger = logger
        self.test_results: List[TestResult] = []
        self.benchmarks: List[PerformanceBenchmark] = []
    
    async def run_validation_tests(
        self,
        adapter: BaseAdapter,
        scenarios: List[TestScenario],
    ) -> List[TestResult]:
        """Run validation tests for an adapter.
        
        Args:
            adapter: Adapter instance to test
            scenarios: List of test scenarios
            
        Returns:
            List of test results
        """
        self.logger.info(f"Running validation tests for adapter: {adapter.config.adapter_id}")
        
        results = []
        
        for scenario in scenarios:
            result = await self._run_scenario(adapter, scenario)
            results.append(result)
            self.test_results.append(result)
        
        # Summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        self.logger.info(f"Validation tests: {passed}/{total} passed")
        
        return results
    
    async def run_performance_benchmark(
        self,
        adapter: BaseAdapter,
        scenario: TestScenario,
        iterations: int = 10,
        concurrent: int = 1,
    ) -> PerformanceBenchmark:
        """Run performance benchmark for an adapter.
        
        Args:
            adapter: Adapter instance to benchmark
            scenario: Test scenario to use
            iterations: Number of iterations
            concurrent: Number of concurrent requests
            
        Returns:
            Performance benchmark results
        """
        self.logger.info(
            f"Running performance benchmark for adapter: {adapter.config.adapter_id} "
            f"({iterations} iterations, {concurrent} concurrent)"
        )
        
        latencies = []
        tokens_list = []
        costs_list = []
        
        async def run_single_request() -> tuple:
            """Run a single request and return metrics."""
            start_time = time.time()
            
            context = self._create_context(scenario)
            result = await adapter.execute(context)
            
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
            
            if result.tokens_used:
                tokens_list.append(result.tokens_used)
            if result.cost_usd:
                costs_list.append(result.cost_usd)
            
            return latency_ms
        
        # Run benchmark
        if concurrent == 1:
            # Sequential execution
            for _ in range(iterations):
                await run_single_request()
        else:
            # Concurrent execution
            tasks = []
            for i in range(iterations):
                if len(tasks) >= concurrent:
                    await asyncio.gather(*tasks)
                    tasks = []
                tasks.append(asyncio.create_task(run_single_request()))
            
            if tasks:
                await asyncio.gather(*tasks)
        
        # Calculate metrics
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        
        throughput_rps = 1000.0 / avg_latency if avg_latency > 0 else 0.0
        
        tokens_per_second = None
        if tokens_list:
            avg_tokens = sum(tokens_list) / len(tokens_list)
            tokens_per_second = avg_tokens * throughput_rps if throughput_rps > 0 else 0.0
        
        cost_per_request = sum(costs_list) / len(costs_list) if costs_list else None
        
        benchmark = PerformanceBenchmark(
            adapter_id=adapter.config.adapter_id,
            test_name=scenario.name,
            latency_ms=avg_latency,
            throughput_rps=throughput_rps,
            tokens_per_second=tokens_per_second,
            cost_per_request=cost_per_request,
            metadata={
                "iterations": iterations,
                "concurrent": concurrent,
                "min_latency_ms": min_latency,
                "max_latency_ms": max_latency,
            },
        )
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    async def _run_scenario(
        self,
        adapter: BaseAdapter,
        scenario: TestScenario,
    ) -> TestResult:
        """Run a single test scenario."""
        start_time = time.time()
        
        try:
            context = self._create_context(scenario)
            result = await adapter.execute(context)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Validate result
            passed = self._validate_result(result, scenario)
            
            return TestResult(
                scenario_name=scenario.name,
                passed=passed,
                latency_ms=latency_ms,
                confidence=result.confidence,
                actual_output=result.output_data,
                metadata={
                    "tokens_used": result.tokens_used,
                    "cost_usd": result.cost_usd,
                },
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestResult(
                scenario_name=scenario.name,
                passed=False,
                latency_ms=latency_ms,
                confidence=0.0,
                error=str(e),
            )
    
    def _create_context(self, scenario: TestScenario) -> ExecutionContext:
        """Create execution context from scenario."""
        node = Node(
            id="test_node",
            kind=NodeKind.AI,
        )
        
        execution_profile = ExecutionProfile()
        
        return ExecutionContext(
            node=node,
            session_id="test_session",
            trace_id="test_trace",
            input_data=scenario.input_data,
            execution_profile=execution_profile,
        )
    
    def _validate_result(
        self,
        result: ExecutionResult,
        scenario: TestScenario,
    ) -> bool:
        """Validate test result against scenario expectations."""
        # Check success
        if not result.success:
            return False
        
        # Check latency
        if result.latency_ms > scenario.max_latency_ms:
            return False
        
        # Check confidence
        if result.confidence < scenario.min_confidence:
            return False
        
        # Check expected output
        if scenario.expected_output is not None:
            if result.output_data != scenario.expected_output:
                return False
        
        # Check expected pattern
        if scenario.expected_pattern:
            output_str = str(result.output_data)
            if scenario.expected_pattern not in output_str:
                return False
        
        return True
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report.
        
        Returns:
            Test report dictionary
        """
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        avg_latency = (
            sum(r.latency_ms for r in self.test_results) / total_tests
            if total_tests > 0 else 0.0
        )
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            },
            "performance": {
                "average_latency_ms": avg_latency,
                "benchmarks": [
                    {
                        "adapter_id": b.adapter_id,
                        "test_name": b.test_name,
                        "latency_ms": b.latency_ms,
                        "throughput_rps": b.throughput_rps,
                        "tokens_per_second": b.tokens_per_second,
                        "cost_per_request": b.cost_per_request,
                    }
                    for b in self.benchmarks
                ],
            },
            "test_results": [
                {
                    "scenario_name": r.scenario_name,
                    "passed": r.passed,
                    "latency_ms": r.latency_ms,
                    "confidence": r.confidence,
                    "error": r.error,
                }
                for r in self.test_results
            ],
        }

