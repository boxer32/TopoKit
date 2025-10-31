"""Policy engine with Rego integration for TopoKit."""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from pathlib import Path

try:
    import opa
    REGO_AVAILABLE = True
except ImportError:
    REGO_AVAILABLE = False
    opa = None

from ..types.topology import Node, EdgePolicy, TopologyPack
from ..types.validation import ValidationResult, ValidationError, ValidationErrorType


class PolicyDecision(str, Enum):
    """Policy decision types."""
    ALLOW = "allow"
    DENY = "deny"
    TRANSFORM = "transform"
    HUMAN_REVIEW = "human_review"


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    message: str
    metadata: Dict[str, Any]
    transformed_data: Optional[Any] = None
    required_approvals: List[str] = None


@dataclass
class PolicyRule:
    """Policy rule definition."""
    name: str
    description: str
    rego_code: str
    priority: int = 0
    enabled: bool = True


class PolicyEngine:
    """Policy engine with Rego integration for TopoKit."""
    
    def __init__(self, policy_dir: Optional[str] = None):
        """Initialize policy engine.
        
        Args:
            policy_dir: Directory containing .rego policy files
        """
        self.policy_dir = Path(policy_dir) if policy_dir else None
        self.rules: Dict[str, PolicyRule] = {}
        self.logger = logging.getLogger(__name__)
        
        if not REGO_AVAILABLE:
            self.logger.warning("OPA Python library not available. Policy engine will use fallback validation.")
    
    async def load_policies(self, policy_dir: Optional[str] = None) -> bool:
        """Load policies from directory.
        
        Args:
            policy_dir: Directory containing .rego files
            
        Returns:
            True if policies loaded successfully
        """
        if policy_dir:
            self.policy_dir = Path(policy_dir)
        
        if not self.policy_dir or not self.policy_dir.exists():
            self.logger.warning(f"Policy directory not found: {self.policy_dir}")
            return False
        
        try:
            # Load all .rego files
            rego_files = list(self.policy_dir.glob("*.rego"))
            if not rego_files:
                self.logger.warning(f"No .rego files found in {self.policy_dir}")
                return False
            
            for rego_file in rego_files:
                await self._load_policy_file(rego_file)
            
            self.logger.info(f"Loaded {len(self.rules)} policy rules from {len(rego_files)} files")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load policies: {e}")
            return False
    
    async def _load_policy_file(self, file_path: Path) -> None:
        """Load a single policy file.
        
        Args:
            file_path: Path to .rego file
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract rule name from file name or content
            rule_name = file_path.stem
            
            # Parse Rego content to extract description and priority
            description = self._extract_description(content)
            priority = self._extract_priority(content)
            
            rule = PolicyRule(
                name=rule_name,
                description=description,
                rego_code=content,
                priority=priority,
                enabled=True
            )
            
            self.rules[rule_name] = rule
            self.logger.debug(f"Loaded policy rule: {rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to load policy file {file_path}: {e}")
    
    def _extract_description(self, content: str) -> str:
        """Extract description from Rego content.
        
        Args:
            content: Rego policy content
            
        Returns:
            Description string
        """
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('# Description:'):
                return line.replace('# Description:', '').strip()
        return "Policy rule"
    
    def _extract_priority(self, content: str) -> int:
        """Extract priority from Rego content.
        
        Args:
            content: Rego policy content
            
        Returns:
            Priority integer
        """
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('# Priority:'):
                try:
                    return int(line.replace('# Priority:', '').strip())
                except ValueError:
                    pass
        return 0
    
    async def evaluate_policy(self, 
                            data: Any, 
                            node: Node, 
                            edge: Optional[EdgePolicy] = None,
                            context: Optional[Dict[str, Any]] = None) -> PolicyResult:
        """Evaluate policies against data and node.
        
        Args:
            data: Data to evaluate
            node: Node context
            edge: Edge context (optional)
            context: Additional context
            
        Returns:
            Policy evaluation result
        """
        if not self.rules:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                message="No policies loaded",
                metadata={}
            )
        
        # Prepare input for Rego evaluation
        input_data = {
            "data": data,
            "node": {
                "id": node.id,
                "kind": node.kind,
                "version": node.version,
                "scope": node.scope.dict() if hasattr(node.scope, 'dict') else node.scope
            },
            "context": context or {}
        }
        
        if edge:
            input_data["edge"] = {
                "id": edge.id,
                "from": edge.from_node,
                "to": edge.to_node,
                "version": edge.version,
                "contracts": edge.contracts,
                "allow": edge.allow
            }
        
        # Evaluate rules in priority order
        sorted_rules = sorted(self.rules.values(), key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            try:
                result = await self._evaluate_rule(rule, input_data)
                if result.decision != PolicyDecision.ALLOW:
                    return result
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {e}")
                continue
        
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            message="All policies passed",
            metadata={"evaluated_rules": len(sorted_rules)}
        )
    
    async def _evaluate_rule(self, rule: PolicyRule, input_data: Dict[str, Any]) -> PolicyResult:
        """Evaluate a single policy rule.
        
        Args:
            rule: Policy rule to evaluate
            input_data: Input data for evaluation
            
        Returns:
            Policy evaluation result
        """
        if REGO_AVAILABLE and opa:
            return await self._evaluate_with_rego(rule, input_data)
        else:
            return await self._evaluate_with_fallback(rule, input_data)
    
    async def _evaluate_with_rego(self, rule: PolicyRule, input_data: Dict[str, Any]) -> PolicyResult:
        """Evaluate rule using OPA Rego engine.
        
        Args:
            rule: Policy rule to evaluate
            input_data: Input data for evaluation
            
        Returns:
            Policy evaluation result
        """
        try:
            # Create OPA client
            client = opa.Client()
            
            # Compile policy
            policy = client.compile(rule.rego_code)
            
            # Evaluate policy
            result = policy.evaluate(input_data)
            
            # Parse result
            if result.get("allow", False):
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    message=f"Rule {rule.name} passed",
                    metadata={"rule": rule.name, "rego_result": result}
                )
            elif result.get("deny", False):
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    message=f"Rule {rule.name} denied: {result.get('message', 'No reason provided')}",
                    metadata={"rule": rule.name, "rego_result": result}
                )
            elif result.get("transform", False):
                return PolicyResult(
                    decision=PolicyDecision.TRANSFORM,
                    message=f"Rule {rule.name} requires transformation",
                    metadata={"rule": rule.name, "rego_result": result},
                    transformed_data=result.get("transformed_data", input_data["data"])
                )
            elif result.get("human_review", False):
                return PolicyResult(
                    decision=PolicyDecision.HUMAN_REVIEW,
                    message=f"Rule {rule.name} requires human review",
                    metadata={"rule": rule.name, "rego_result": result},
                    required_approvals=result.get("required_approvals", [])
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    message=f"Rule {rule.name} passed (no explicit decision)",
                    metadata={"rule": rule.name, "rego_result": result}
                )
                
        except Exception as e:
            self.logger.error(f"Error evaluating Rego rule {rule.name}: {e}")
            return PolicyResult(
                decision=PolicyDecision.DENY,
                message=f"Error evaluating rule {rule.name}: {e}",
                metadata={"rule": rule.name, "error": str(e)}
            )
    
    async def _evaluate_with_fallback(self, rule: PolicyRule, input_data: Dict[str, Any]) -> PolicyResult:
        """Evaluate rule using fallback validation when Rego is not available.
        
        Args:
            rule: Policy rule to evaluate
            input_data: Input data for evaluation
            
        Returns:
            Policy evaluation result
        """
        # Basic fallback validation
        data = input_data.get("data")
        node = input_data.get("node", {})
        
        # Simple validation rules
        if isinstance(data, dict):
            # Check for required fields
            if "content" in data and isinstance(data["content"], str):
                content = data["content"]
                
                # Basic content validation
                if len(content) > 10000:  # Max content length
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        message=f"Content too long: {len(content)} characters",
                        metadata={"rule": rule.name, "max_length": 10000}
                    )
                
                # Basic PII detection
                if any(pattern in content.lower() for pattern in ["@", "phone", "ssn", "credit"]):
                    return PolicyResult(
                        decision=PolicyDecision.HUMAN_REVIEW,
                        message="Potential PII detected, requires human review",
                        metadata={"rule": rule.name, "pii_detected": True}
                    )
        
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            message=f"Fallback validation passed for rule {rule.name}",
            metadata={"rule": rule.name, "fallback": True}
        )
    
    async def validate_topology(self, topology: TopologyPack) -> ValidationResult:
        """Validate topology against all policies.
        
        Args:
            topology: Topology pack to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        try:
            # Validate nodes
            for node in topology.nodes:
                result = await self.evaluate_policy(
                    data={"node_id": node.id, "kind": node.kind},
                    node=node
                )
                
                if result.decision == PolicyDecision.DENY:
                    errors.append(ValidationError(
                        type=ValidationErrorType.POLICY_ERROR,
                        message=f"Node {node.id} violates policy: {result.message}",
                        path=f"nodes.{node.id}",
                        severity="high",
                        repairable=False
                    ))
            
            # Validate edges
            for edge in topology.edges:
                result = await self.evaluate_policy(
                    data={"edge_id": edge.id, "from": edge.from_node, "to": edge.to_node},
                    node=Node(id=edge.from_node, kind="ai"),  # Dummy node for validation
                    edge=edge
                )
                
                if result.decision == PolicyDecision.DENY:
                    errors.append(ValidationError(
                        type=ValidationErrorType.POLICY_ERROR,
                        message=f"Edge {edge.id} violates policy: {result.message}",
                        path=f"edges.{edge.id}",
                        severity="high",
                        repairable=False
                    ))
            
            return ValidationResult(
                success=len(errors) == 0,
                data=topology,
                errors=errors
            )
            
        except Exception as e:
            errors.append(ValidationError(
                type=ValidationErrorType.UNKNOWN_ERROR,
                message=f"Policy validation error: {e}",
                path="topology",
                severity="critical",
                repairable=False
            ))
            
            return ValidationResult(
                success=False,
                data=topology,
                errors=errors
            )
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of loaded policies.
        
        Returns:
            Policy summary information
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "rules": [
                {
                    "name": rule.name,
                    "description": rule.description,
                    "priority": rule.priority,
                    "enabled": rule.enabled
                }
                for rule in self.rules.values()
            ],
            "rego_available": REGO_AVAILABLE
        }
