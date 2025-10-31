"""Replay harness with deterministic testing in TopoKit."""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import yaml

from ..types.topology import TopologyPack
from .orchestrator import EnhancedTopoOrchestrator


class ReplayResult(str):
    """Replay execution result."""
    IDENTICAL = "identical"
    DIFFERENT = "different"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class GoldenCase:
    """Golden case definition for deterministic testing."""
    id: str
    name: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    expected_execution_path: List[str]
    expected_execution_time_ms: Optional[float] = None
    seed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayExecution:
    """Replay execution record."""
    golden_case_id: str
    execution_id: str
    execution_path: List[str]
    execution_output: Dict[str, Any]
    execution_time_ms: float
    seed: str
    trace_hash: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    matches_golden: bool = False
    differences: List[str] = field(default_factory=list)
    performance_regression: Optional[float] = None


class SeedLockManager:
    """Manages seed-lock testing for identical outputs across runs."""
    
    def __init__(self, seed_base: Optional[str] = None):
        """Initialize seed lock manager."""
        self.seed_base = seed_base or "deterministic"
        self._seed_cache: Dict[str, str] = {}
    
    def get_seed(self, case_id: str, input_hash: str) -> str:
        """Get deterministic seed for a test case."""
        cache_key = f"{case_id}:{input_hash}"
        if cache_key not in self._seed_cache:
            # Generate deterministic seed
            seed_input = f"{self.seed_base}:{case_id}:{input_hash}"
            self._seed_cache[cache_key] = hashlib.sha256(seed_input.encode()).hexdigest()[:16]
        return self._seed_cache[cache_key]
    
    def lock_seed(self, case_id: str, seed: str) -> None:
        """Lock a seed for a test case."""
        self._seed_cache[case_id] = seed


class DeterministicReplayer:
    """Provides deterministic replay with exact execution paths."""
    
    def __init__(self, seed_manager: Optional[SeedLockManager] = None):
        """Initialize deterministic replayer."""
        self.seed_manager = seed_manager or SeedLockManager()
        self._execution_cache: Dict[str, Dict[str, Any]] = {}
    
    async def replay(
        self,
        orchestrator: EnhancedTopoOrchestrator,
        golden_case: GoldenCase,
        entry_node: str
    ) -> ReplayExecution:
        """Replay execution with deterministic settings."""
        # Generate input hash for seed generation
        input_str = json.dumps(golden_case.input_data, sort_keys=True)
        input_hash = hashlib.md5(input_str.encode()).hexdigest()
        
        # Get deterministic seed
        seed = golden_case.seed or self.seed_manager.get_seed(golden_case.id, input_hash)
        
        # Execute with deterministic settings
        start_time = time.time()
        execution_result = await orchestrator.execute(
            session_id=f"replay_{golden_case.id}_{int(time.time())}",
            input_data=golden_case.input_data,
            entry_node=entry_node,
            timeout_seconds=300,
            deterministic_seed=seed
        )
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Extract execution path
        execution_path = execution_result.get("nodes_executed", [])
        
        # Generate trace hash
        trace_data = {
            "path": execution_path,
            "output": execution_result.get("output", {}),
            "seed": seed
        }
        trace_hash = hashlib.sha256(json.dumps(trace_data, sort_keys=True).encode()).hexdigest()
        
        # Compare with golden case
        matches_golden, differences = self._compare_with_golden(
            golden_case,
            execution_path,
            execution_result.get("output", {}),
            execution_time_ms
        )
        
        return ReplayExecution(
            golden_case_id=golden_case.id,
            execution_id=execution_result.get("trace_id", ""),
            execution_path=execution_path,
            execution_output=execution_result.get("output", {}),
            execution_time_ms=execution_time_ms,
            seed=seed,
            trace_hash=trace_hash,
            matches_golden=matches_golden,
            differences=differences
        )
    
    def _compare_with_golden(
        self,
        golden_case: GoldenCase,
        execution_path: List[str],
        execution_output: Dict[str, Any],
        execution_time_ms: float
    ) -> Tuple[bool, List[str]]:
        """Compare execution with golden case."""
        differences = []
        matches = True
        
        # Compare execution path
        if execution_path != golden_case.expected_execution_path:
            differences.append(
                f"Execution path mismatch: expected {golden_case.expected_execution_path}, "
                f"got {execution_path}"
            )
            matches = False
        
        # Compare output
        if execution_output != golden_case.expected_output:
            differences.append(
                f"Output mismatch: expected {golden_case.expected_output}, got {execution_output}"
            )
            matches = False
        
        # Compare execution time (with tolerance)
        if golden_case.expected_execution_time_ms:
            time_diff = abs(execution_time_ms - golden_case.expected_execution_time_ms)
            tolerance = golden_case.expected_execution_time_ms * 0.1  # 10% tolerance
            if time_diff > tolerance:
                differences.append(
                    f"Execution time mismatch: expected {golden_case.expected_execution_time_ms}ms, "
                    f"got {execution_time_ms}ms (diff: {time_diff}ms)"
                )
                matches = False
        
        return matches, differences


class GoldenCaseValidator:
    """Validates executions against golden cases."""
    
    def __init__(self, golden_cases_dir: Optional[Path] = None):
        """Initialize golden case validator."""
        self.golden_cases_dir = golden_cases_dir or Path("./topology/eval/golden")
        self._golden_cases: Dict[str, GoldenCase] = {}
        self._load_golden_cases()
    
    def _load_golden_cases(self) -> None:
        """Load golden cases from directory."""
        if not self.golden_cases_dir.exists():
            return
        
        for case_file in self.golden_cases_dir.glob("*.yaml"):
            try:
                with open(case_file, 'r') as f:
                    case_data = yaml.safe_load(f)
                    
                golden_case = GoldenCase(
                    id=case_data.get("id", case_file.stem),
                    name=case_data.get("name", case_file.stem),
                    input_data=case_data.get("input", {}),
                    expected_output=case_data.get("expected_output", {}),
                    expected_execution_path=case_data.get("expected_path", []),
                    expected_execution_time_ms=case_data.get("expected_time_ms"),
                    seed=case_data.get("seed"),
                    metadata=case_data.get("metadata", {})
                )
                
                self._golden_cases[golden_case.id] = golden_case
            except Exception as e:
                print(f"Warning: Failed to load golden case {case_file}: {e}")
    
    def get_golden_case(self, case_id: str) -> Optional[GoldenCase]:
        """Get golden case by ID."""
        return self._golden_cases.get(case_id)
    
    def get_all_golden_cases(self) -> List[GoldenCase]:
        """Get all golden cases."""
        return list(self._golden_cases.values())


class PerformanceRegressionTracker:
    """Tracks performance regression across executions."""
    
    def __init__(self):
        """Initialize performance regression tracker."""
        self._baseline_metrics: Dict[str, Dict[str, float]] = {}
        self._execution_history: List[Dict[str, Any]] = []
    
    def set_baseline(
        self,
        case_id: str,
        execution_time_ms: float,
        other_metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """Set baseline performance metrics."""
        self._baseline_metrics[case_id] = {
            "execution_time_ms": execution_time_ms,
            **(other_metrics or {})
        }
    
    def check_regression(
        self,
        case_id: str,
        execution_time_ms: float,
        other_metrics: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, Optional[float]]:
        """Check for performance regression."""
        if case_id not in self._baseline_metrics:
            return False, None
        
        baseline = self._baseline_metrics[case_id]
        baseline_time = baseline["execution_time_ms"]
        
        # Calculate regression percentage
        regression_percent = ((execution_time_ms - baseline_time) / baseline_time) * 100.0
        
        # Check if regression exceeds threshold (e.g., 20%)
        regression_detected = regression_percent > 20.0
        
        # Record execution
        execution_record = {
            "case_id": case_id,
            "execution_time_ms": execution_time_ms,
            "baseline_time_ms": baseline_time,
            "regression_percent": regression_percent,
            "timestamp": datetime.utcnow(),
            "other_metrics": other_metrics or {}
        }
        self._execution_history.append(execution_record)
        
        return regression_detected, regression_percent
    
    def get_regression_history(self, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get performance regression history."""
        if case_id:
            return [h for h in self._execution_history if h["case_id"] == case_id]
        return self._execution_history


class ReplayHarness:
    """Replay harness for deterministic testing."""
    
    def __init__(
        self,
        seed_manager: Optional[SeedLockManager] = None,
        golden_validator: Optional[GoldenCaseValidator] = None,
        performance_tracker: Optional[PerformanceRegressionTracker] = None
    ):
        """Initialize replay harness."""
        self.seed_manager = seed_manager or SeedLockManager()
        self.golden_validator = golden_validator or GoldenCaseValidator()
        self.performance_tracker = performance_tracker or PerformanceRegressionTracker()
        self.replayer = DeterministicReplayer(self.seed_manager)
    
    async def replay_golden_case(
        self,
        orchestrator: EnhancedTopoOrchestrator,
        case_id: str,
        entry_node: str
    ) -> ReplayExecution:
        """Replay a golden case and validate against expected output."""
        golden_case = self.golden_validator.get_golden_case(case_id)
        if not golden_case:
            raise ValueError(f"Golden case not found: {case_id}")
        
        # Replay execution
        execution = await self.replayer.replay(orchestrator, golden_case, entry_node)
        
        # Check performance regression
        regression_detected, regression_percent = self.performance_tracker.check_regression(
            case_id,
            execution.execution_time_ms
        )
        
        if regression_detected:
            execution.performance_regression = regression_percent
        
        # Set baseline if this is first run
        if case_id not in self.performance_tracker._baseline_metrics:
            self.performance_tracker.set_baseline(case_id, execution.execution_time_ms)
        
        return execution
    
    async def replay_all_golden_cases(
        self,
        orchestrator: EnhancedTopoOrchestrator,
        entry_node: str
    ) -> List[ReplayExecution]:
        """Replay all golden cases."""
        golden_cases = self.golden_validator.get_all_golden_cases()
        results = []
        
        for golden_case in golden_cases:
            try:
                execution = await self.replay_golden_case(
                    orchestrator,
                    golden_case.id,
                    entry_node
                )
                results.append(execution)
            except Exception as e:
                # Create error execution record
                error_execution = ReplayExecution(
                    golden_case_id=golden_case.id,
                    execution_id="",
                    execution_path=[],
                    execution_output={},
                    execution_time_ms=0.0,
                    seed="",
                    trace_hash="",
                    matches_golden=False,
                    differences=[f"Error: {str(e)}"]
                )
                results.append(error_execution)
        
        return results
    
    def save_golden_case(self, case: GoldenCase, output_path: Optional[Path] = None) -> None:
        """Save a golden case to file."""
        if output_path is None:
            output_path = self.golden_validator.golden_cases_dir / f"{case.id}.yaml"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        case_data = {
            "id": case.id,
            "name": case.name,
            "input": case.input_data,
            "expected_output": case.expected_output,
            "expected_path": case.expected_execution_path,
            "expected_time_ms": case.expected_execution_time_ms,
            "seed": case.seed,
            "metadata": case.metadata
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(case_data, f, default_flow_style=False)

