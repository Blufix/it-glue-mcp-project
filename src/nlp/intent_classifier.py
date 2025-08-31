"""Intent classification for natural language IT queries."""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Types of query intents."""
    # Information retrieval
    RETRIEVAL = "retrieval"          # Get/show/list information
    SEARCH = "search"                # Find/search for items
    
    # Troubleshooting & Investigation
    TROUBLESHOOTING = "troubleshooting"    # Fix errors, debug issues
    INVESTIGATION = "investigation"        # Who/what/when changed something
    ROOT_CAUSE = "root_cause"             # Find cause of issue
    
    # Analysis & Reporting
    AUDIT = "audit"                  # Security/compliance auditing
    ANALYSIS = "analysis"            # Analyze dependencies, impact
    COMPARISON = "comparison"        # Compare configurations
    MONITORING = "monitoring"        # Check status, health
    
    # Documentation & Help
    DOCUMENTATION = "documentation"  # How-to guides, procedures
    HELP = "help"                    # General help requests
    
    # Actions
    CONFIGURATION = "configuration"  # Setup, configure, install
    UPDATE = "update"               # Update, patch, upgrade
    BACKUP = "backup"               # Backup, restore operations
    
    # Relationship queries
    DEPENDENCY = "dependency"       # What depends on what
    IMPACT = "impact"              # What's affected by changes
    TOPOLOGY = "topology"          # Network/service maps
    
    # Unknown
    UNKNOWN = "unknown"            # Cannot determine intent


@dataclass
class IntentClassification:
    """Result of intent classification."""
    primary_intent: QueryIntent
    confidence: float
    secondary_intents: List[Tuple[QueryIntent, float]] = field(default_factory=list)
    query_strategy: str = ""
    keywords_matched: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    

@dataclass
class IntentPattern:
    """Pattern for matching query intent."""
    intent: QueryIntent
    patterns: List[re.Pattern]
    keywords: List[str]
    weight: float = 1.0
    context_boost: Dict[str, float] = field(default_factory=dict)
    

class IntentClassifier:
    """Classify the intent of natural language IT queries."""
    
    def __init__(self):
        """Initialize the intent classifier."""
        self.intent_patterns = self._build_intent_patterns()
        self.strategy_mappings = self._build_strategy_mappings()
        self.action_mappings = self._build_action_mappings()
        
    def _build_intent_patterns(self) -> List[IntentPattern]:
        """Build patterns for intent classification."""
        return [
            # RETRIEVAL
            IntentPattern(
                intent=QueryIntent.RETRIEVAL,
                patterns=[
                    re.compile(r'\b(show|list|get|display|view|fetch)\b', re.I),
                    re.compile(r'\bwhat (?:is|are)\b', re.I),
                    re.compile(r'\bgive me\b', re.I),
                ],
                keywords=["show", "list", "get", "display", "view", "fetch", "retrieve"],
                weight=1.0
            ),
            
            # SEARCH
            IntentPattern(
                intent=QueryIntent.SEARCH,
                patterns=[
                    re.compile(r'\b(find|search|locate|look for|where)\b', re.I),
                    re.compile(r'\bdo we have\b', re.I),
                    re.compile(r'\bis there\b', re.I),
                ],
                keywords=["find", "search", "locate", "lookup", "where"],
                weight=1.0
            ),
            
            # TROUBLESHOOTING
            IntentPattern(
                intent=QueryIntent.TROUBLESHOOTING,
                patterns=[
                    re.compile(r'\b(error|fail|failed|failing|broken|not working|issue|problem)\b', re.I),
                    re.compile(r'\b(fix|resolve|troubleshoot|debug|diagnose)\b', re.I),
                    re.compile(r'\b(down|offline|unreachable|timeout|crashed)\b', re.I),
                    re.compile(r'\bwhy (?:is|are|does|doesn\'t)\b', re.I),
                ],
                keywords=["error", "fail", "broken", "fix", "troubleshoot", "debug", "issue", "problem"],
                weight=1.2,
                context_boost={"recent": 1.5, "urgent": 2.0}
            ),
            
            # INVESTIGATION
            IntentPattern(
                intent=QueryIntent.INVESTIGATION,
                patterns=[
                    re.compile(r'\b(who|when|what|how) (?:changed|modified|updated|deleted|created)\b', re.I),
                    re.compile(r'\b(investigate|trace|track|history|log|audit trail)\b', re.I),
                    re.compile(r'\b(recent|last|latest) (?:change|modification|update)\b', re.I),
                ],
                keywords=["who", "when", "what", "changed", "modified", "investigate", "audit"],
                weight=1.1
            ),
            
            # ROOT_CAUSE
            IntentPattern(
                intent=QueryIntent.ROOT_CAUSE,
                patterns=[
                    re.compile(r'\b(root cause|why|cause|reason|source)\b', re.I),
                    re.compile(r'\bwhat caused\b', re.I),
                    re.compile(r'\bfind (?:the )?(?:root )?cause\b', re.I),
                ],
                keywords=["root", "cause", "why", "reason", "source"],
                weight=1.3
            ),
            
            # AUDIT
            IntentPattern(
                intent=QueryIntent.AUDIT,
                patterns=[
                    re.compile(r'\b(audit|compliance|security|review|check|verify)\b', re.I),
                    re.compile(r'\b(expired|expiring|old|stale|unused|orphaned)\b', re.I),
                    re.compile(r'\b(password|credential|certificate) (?:audit|review|check)\b', re.I),
                ],
                keywords=["audit", "compliance", "security", "review", "expired", "verify"],
                weight=1.1
            ),
            
            # ANALYSIS
            IntentPattern(
                intent=QueryIntent.ANALYSIS,
                patterns=[
                    re.compile(r'\b(analyze|analysis|examine|evaluate|assess)\b', re.I),
                    re.compile(r'\b(pattern|trend|statistics|metrics)\b', re.I),
                    re.compile(r'\bhow many\b', re.I),
                ],
                keywords=["analyze", "analysis", "examine", "evaluate", "metrics", "statistics"],
                weight=1.0
            ),
            
            # COMPARISON
            IntentPattern(
                intent=QueryIntent.COMPARISON,
                patterns=[
                    re.compile(r'\b(compare|diff|difference|versus|vs\.?|between)\b', re.I),
                    re.compile(r'\b(same|similar|different|match)\b', re.I),
                ],
                keywords=["compare", "diff", "difference", "versus", "between", "similar"],
                weight=1.0
            ),
            
            # MONITORING
            IntentPattern(
                intent=QueryIntent.MONITORING,
                patterns=[
                    re.compile(r'\b(status|health|check|monitor|ping|alive|running)\b', re.I),
                    re.compile(r'\b(performance|metrics|usage|utilization)\b', re.I),
                    re.compile(r'\bis (?:it |the )?(?:up|down|running|active)\b', re.I),
                ],
                keywords=["status", "health", "monitor", "check", "performance", "metrics"],
                weight=1.0
            ),
            
            # DOCUMENTATION
            IntentPattern(
                intent=QueryIntent.DOCUMENTATION,
                patterns=[
                    re.compile(r'\b(how to|how do|guide|manual|documentation|procedure|instructions)\b', re.I),
                    re.compile(r'\b(tutorial|example|sample|template)\b', re.I),
                    re.compile(r'\bsteps (?:to|for)\b', re.I),
                ],
                keywords=["how", "guide", "manual", "documentation", "procedure", "tutorial"],
                weight=1.0
            ),
            
            # CONFIGURATION
            IntentPattern(
                intent=QueryIntent.CONFIGURATION,
                patterns=[
                    re.compile(r'\b(configure|setup|install|deploy|enable|disable)\b', re.I),
                    re.compile(r'\b(setting|parameter|option|preference)\b', re.I),
                ],
                keywords=["configure", "setup", "install", "deploy", "setting"],
                weight=1.0
            ),
            
            # UPDATE
            IntentPattern(
                intent=QueryIntent.UPDATE,
                patterns=[
                    re.compile(r'\b(update|upgrade|patch|migrate|refresh)\b', re.I),
                    re.compile(r'\b(new version|latest|current)\b', re.I),
                ],
                keywords=["update", "upgrade", "patch", "migrate", "version"],
                weight=1.0
            ),
            
            # BACKUP
            IntentPattern(
                intent=QueryIntent.BACKUP,
                patterns=[
                    re.compile(r'\b(backup|restore|recover|snapshot|archive)\b', re.I),
                    re.compile(r'\b(disaster recovery|dr|business continuity)\b', re.I),
                ],
                keywords=["backup", "restore", "recover", "snapshot", "archive"],
                weight=1.0
            ),
            
            # DEPENDENCY
            IntentPattern(
                intent=QueryIntent.DEPENDENCY,
                patterns=[
                    re.compile(r'\b(depend|dependency|dependencies|require|need)\b', re.I),
                    re.compile(r'\bwhat (?:does .+? )?(?:depend|rely) on\b', re.I),
                    re.compile(r'\b(?:upstream|downstream) (?:dependency|service)\b', re.I),
                ],
                keywords=["depend", "dependency", "require", "rely", "upstream", "downstream"],
                weight=1.1
            ),
            
            # IMPACT
            IntentPattern(
                intent=QueryIntent.IMPACT,
                patterns=[
                    re.compile(r'\b(impact|affect|consequence|result|blast radius)\b', re.I),
                    re.compile(r'\bwhat (?:will )?happen(?:s)? (?:if|when)\b', re.I),
                    re.compile(r'\bif .+? (?:fails|goes down|stops)\b', re.I),
                ],
                keywords=["impact", "affect", "consequence", "blast", "radius", "happen"],
                weight=1.2
            ),
            
            # TOPOLOGY
            IntentPattern(
                intent=QueryIntent.TOPOLOGY,
                patterns=[
                    re.compile(r'\b(topology|map|diagram|layout|architecture)\b', re.I),
                    re.compile(r'\b(network|service|system) (?:map|topology|diagram)\b', re.I),
                    re.compile(r'\bhow (?:are |is ).+? connected\b', re.I),
                ],
                keywords=["topology", "map", "diagram", "architecture", "connected"],
                weight=1.0
            ),
        ]
        
    def _build_strategy_mappings(self) -> Dict[QueryIntent, str]:
        """Map intents to query strategies."""
        return {
            QueryIntent.RETRIEVAL: "direct_query",
            QueryIntent.SEARCH: "fuzzy_search",
            QueryIntent.TROUBLESHOOTING: "diagnostic_analysis",
            QueryIntent.INVESTIGATION: "audit_trail",
            QueryIntent.ROOT_CAUSE: "root_cause_analysis",
            QueryIntent.AUDIT: "compliance_check",
            QueryIntent.ANALYSIS: "statistical_analysis",
            QueryIntent.COMPARISON: "comparative_analysis",
            QueryIntent.MONITORING: "status_check",
            QueryIntent.DOCUMENTATION: "knowledge_search",
            QueryIntent.CONFIGURATION: "config_guide",
            QueryIntent.UPDATE: "version_check",
            QueryIntent.BACKUP: "backup_status",
            QueryIntent.DEPENDENCY: "dependency_graph",
            QueryIntent.IMPACT: "impact_analysis",
            QueryIntent.TOPOLOGY: "topology_mapping",
            QueryIntent.UNKNOWN: "general_search"
        }
        
    def _build_action_mappings(self) -> Dict[QueryIntent, List[str]]:
        """Map intents to suggested actions."""
        return {
            QueryIntent.RETRIEVAL: [
                "Execute direct database query",
                "Return matching records",
                "Format results for display"
            ],
            QueryIntent.SEARCH: [
                "Use fuzzy matching",
                "Search across multiple fields",
                "Rank results by relevance"
            ],
            QueryIntent.TROUBLESHOOTING: [
                "Check error logs",
                "Verify service status",
                "Run diagnostic queries",
                "Suggest fixes"
            ],
            QueryIntent.INVESTIGATION: [
                "Query audit logs",
                "Track change history",
                "Identify responsible users",
                "Timeline reconstruction"
            ],
            QueryIntent.ROOT_CAUSE: [
                "Trace dependency chain",
                "Analyze error patterns",
                "Check upstream services",
                "Identify failure point"
            ],
            QueryIntent.AUDIT: [
                "Run compliance checks",
                "Find expired items",
                "Generate audit report",
                "Flag security issues"
            ],
            QueryIntent.DEPENDENCY: [
                "Build dependency graph",
                "Trace relationships",
                "Identify critical paths"
            ],
            QueryIntent.IMPACT: [
                "Calculate blast radius",
                "Identify affected services",
                "Assess criticality",
                "Generate impact report"
            ],
            QueryIntent.TOPOLOGY: [
                "Generate network map",
                "Show service connections",
                "Visualize architecture"
            ]
        }
        
    def classify_intent(self, query: str) -> IntentClassification:
        """Classify the intent of a query."""
        query_lower = query.lower()
        
        # Score each intent
        intent_scores: Dict[QueryIntent, float] = {}
        matched_keywords: Dict[QueryIntent, List[str]] = {}
        
        for pattern_group in self.intent_patterns:
            score = 0.0
            keywords = []
            
            # Check regex patterns
            for pattern in pattern_group.patterns:
                if pattern.search(query):
                    score += pattern_group.weight
                    
            # Check keywords
            for keyword in pattern_group.keywords:
                if keyword.lower() in query_lower:
                    score += 0.5 * pattern_group.weight
                    keywords.append(keyword)
                    
            # Apply context boosts
            for context_word, boost in pattern_group.context_boost.items():
                if context_word in query_lower:
                    score *= boost
                    
            if score > 0:
                intent_scores[pattern_group.intent] = score
                matched_keywords[pattern_group.intent] = keywords
                
        # Determine primary intent
        if not intent_scores:
            return IntentClassification(
                primary_intent=QueryIntent.UNKNOWN,
                confidence=0.0,
                query_strategy=self.strategy_mappings[QueryIntent.UNKNOWN]
            )
            
        # Sort intents by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = sorted_intents[0][0]
        primary_score = sorted_intents[0][1]
        
        # Calculate confidence
        total_score = sum(intent_scores.values())
        confidence = min(primary_score / max(total_score, 1.0), 1.0)
        
        # Get secondary intents
        secondary_intents = [
            (intent, score/total_score) 
            for intent, score in sorted_intents[1:3]
            if score > 0.5
        ]
        
        # Get strategy and actions
        strategy = self.strategy_mappings.get(primary_intent, "general_search")
        actions = self.action_mappings.get(primary_intent, [])
        
        return IntentClassification(
            primary_intent=primary_intent,
            confidence=confidence,
            secondary_intents=secondary_intents,
            query_strategy=strategy,
            keywords_matched=matched_keywords.get(primary_intent, []),
            suggested_actions=actions
        )
        
    def classify_batch(self, queries: List[str]) -> List[IntentClassification]:
        """Classify multiple queries."""
        return [self.classify_intent(query) for query in queries]
        
    def get_intent_distribution(self, queries: List[str]) -> Dict[QueryIntent, float]:
        """Get distribution of intents across multiple queries."""
        classifications = self.classify_batch(queries)
        intent_counts = Counter(c.primary_intent for c in classifications)
        
        total = len(classifications)
        return {
            intent: count/total 
            for intent, count in intent_counts.items()
        }
        
    def suggest_refinement(self, 
                          query: str, 
                          classification: IntentClassification) -> List[str]:
        """Suggest query refinements based on classification."""
        suggestions = []
        
        # Low confidence - suggest clarification
        if classification.confidence < 0.5:
            suggestions.append(f"Clarify if you want to {classification.primary_intent.value}")
            
            # Suggest based on secondary intents
            for intent, _ in classification.secondary_intents:
                suggestions.append(f"Or did you mean to {intent.value}?")
                
        # Specific intent suggestions
        if classification.primary_intent == QueryIntent.TROUBLESHOOTING:
            if "error" not in query.lower():
                suggestions.append("Include the specific error message")
            if "when" not in query.lower():
                suggestions.append("Specify when the issue started")
                
        elif classification.primary_intent == QueryIntent.INVESTIGATION:
            if not any(word in query.lower() for word in ["who", "when", "what"]):
                suggestions.append("Specify what information you need (who/when/what)")
                
        elif classification.primary_intent == QueryIntent.IMPACT:
            if "if" not in query.lower() and "when" not in query.lower():
                suggestions.append("Specify the scenario (e.g., 'if server X fails')")
                
        return suggestions
        
    def is_action_query(self, classification: IntentClassification) -> bool:
        """Check if the query implies an action should be taken."""
        action_intents = {
            QueryIntent.CONFIGURATION,
            QueryIntent.UPDATE,
            QueryIntent.BACKUP,
            QueryIntent.TROUBLESHOOTING
        }
        return classification.primary_intent in action_intents
        
    def get_required_permissions(self, 
                                classification: IntentClassification) -> List[str]:
        """Get required permissions for the classified intent."""
        permission_map = {
            QueryIntent.RETRIEVAL: ["read"],
            QueryIntent.SEARCH: ["read"],
            QueryIntent.TROUBLESHOOTING: ["read", "diagnose"],
            QueryIntent.INVESTIGATION: ["read", "audit"],
            QueryIntent.AUDIT: ["read", "audit"],
            QueryIntent.CONFIGURATION: ["read", "write", "configure"],
            QueryIntent.UPDATE: ["read", "write", "update"],
            QueryIntent.BACKUP: ["read", "backup"],
            QueryIntent.MONITORING: ["read", "monitor"]
        }
        
        return permission_map.get(classification.primary_intent, ["read"])