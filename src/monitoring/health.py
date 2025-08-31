"""Health check system for monitoring service health."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import time
import asyncio
from datetime import datetime, timedelta


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: HealthStatus
    message: str = ""
    last_check: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_critical(self) -> bool:
        """Check if component is critical (unhealthy)."""
        return self.status == HealthStatus.UNHEALTHY


@dataclass 
class HealthCheckResult:
    """Result of a health check."""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.overall_status.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "metadata": c.metadata
                }
                for c in self.components
            ],
            "metadata": self.metadata
        }


class HealthChecker:
    """Perform health checks on system components."""
    
    def __init__(
        self,
        check_interval_seconds: int = 30,
        timeout_seconds: int = 10
    ):
        """
        Initialize health checker.
        
        Args:
            check_interval_seconds: Interval between health checks
            timeout_seconds: Timeout for individual checks
        """
        self.check_interval = check_interval_seconds
        self.timeout = timeout_seconds
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, ComponentHealth] = {}
        self.critical_components: Set[str] = set()
        self._running = False
        
    def register_check(
        self,
        name: str,
        check_func: Callable,
        critical: bool = False
    ):
        """
        Register a health check.
        
        Args:
            name: Component name
            check_func: Function that returns (bool, message, metadata)
            critical: Whether component is critical for overall health
        """
        self.checks[name] = check_func
        if critical:
            self.critical_components.add(name)
    
    async def check_component(
        self,
        name: str,
        check_func: Callable
    ) -> ComponentHealth:
        """
        Check a single component.
        
        Args:
            name: Component name
            check_func: Check function
            
        Returns:
            Component health status
        """
        try:
            # Run check with timeout
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(
                    check_func(),
                    timeout=self.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, check_func),
                    timeout=self.timeout
                )
            
            # Parse result
            if isinstance(result, tuple):
                if len(result) == 3:
                    is_healthy, message, metadata = result
                elif len(result) == 2:
                    is_healthy, message = result
                    metadata = {}
                else:
                    is_healthy = result[0]
                    message = ""
                    metadata = {}
            else:
                is_healthy = bool(result)
                message = "OK" if is_healthy else "Failed"
                metadata = {}
            
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            
            return ComponentHealth(
                name=name,
                status=status,
                message=message,
                metadata=metadata
            )
            
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s"
            )
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )
    
    async def check_all(self) -> HealthCheckResult:
        """
        Run all health checks.
        
        Returns:
            Overall health check result
        """
        start_time = time.time()
        tasks = []
        
        # Create tasks for all checks
        for name, check_func in self.checks.items():
            tasks.append(self.check_component(name, check_func))
        
        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        components = []
        for result in results:
            if isinstance(result, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                ))
            else:
                components.append(result)
                self.last_results[result.name] = result
        
        # Determine overall status
        overall_status = self._calculate_overall_status(components)
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            overall_status=overall_status,
            components=components,
            duration_ms=duration_ms,
            metadata={
                "total_checks": len(self.checks),
                "critical_components": list(self.critical_components)
            }
        )
    
    def _calculate_overall_status(
        self,
        components: List[ComponentHealth]
    ) -> HealthStatus:
        """
        Calculate overall health status.
        
        Args:
            components: Component health statuses
            
        Returns:
            Overall health status
        """
        # If any critical component is unhealthy, overall is unhealthy
        for component in components:
            if component.name in self.critical_components:
                if component.status == HealthStatus.UNHEALTHY:
                    return HealthStatus.UNHEALTHY
        
        # Count statuses
        unhealthy_count = sum(
            1 for c in components 
            if c.status == HealthStatus.UNHEALTHY
        )
        degraded_count = sum(
            1 for c in components
            if c.status == HealthStatus.DEGRADED
        )
        
        # Determine overall status
        if unhealthy_count > 0:
            # Non-critical components unhealthy = degraded
            return HealthStatus.DEGRADED
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def start_background_checks(self):
        """Start background health check loop."""
        self._running = True
        
        while self._running:
            try:
                await self.check_all()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                # Log error but continue checking
                print(f"Health check error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_background_checks(self):
        """Stop background health checks."""
        self._running = False
    
    def get_last_results(self) -> Dict[str, ComponentHealth]:
        """Get last health check results."""
        return self.last_results.copy()
    
    def is_healthy(self) -> bool:
        """Check if system is healthy based on last results."""
        if not self.last_results:
            return False
        
        for name in self.critical_components:
            if name in self.last_results:
                if not self.last_results[name].is_healthy:
                    return False
        
        return True
    
    def register_default_checks(
        self,
        redis_client=None,
        neo4j_driver=None,
        itglue_client=None
    ):
        """
        Register default health checks.
        
        Args:
            redis_client: Redis client instance
            neo4j_driver: Neo4j driver instance
            itglue_client: IT Glue client instance
        """
        # Redis health check
        if redis_client:
            async def check_redis():
                try:
                    await redis_client.ping()
                    info = await redis_client.info()
                    return True, "Redis is healthy", {"connections": info.get("connected_clients", 0)}
                except Exception as e:
                    return False, f"Redis error: {str(e)}", {}
            
            self.register_check("redis", check_redis, critical=True)
        
        # Neo4j health check
        if neo4j_driver:
            async def check_neo4j():
                try:
                    async with neo4j_driver.session() as session:
                        result = await session.run("RETURN 1 as health")
                        await result.single()
                    return True, "Neo4j is healthy", {}
                except Exception as e:
                    return False, f"Neo4j error: {str(e)}", {}
            
            self.register_check("neo4j", check_neo4j, critical=True)
        
        # IT Glue API health check
        if itglue_client:
            async def check_itglue():
                try:
                    # Simple API call to check connectivity
                    response = await itglue_client.get("/organizations?page[size]=1")
                    return True, "IT Glue API is accessible", {
                        "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining", "unknown")
                    }
                except Exception as e:
                    return False, f"IT Glue API error: {str(e)}", {}
            
            self.register_check("itglue_api", check_itglue, critical=False)
        
        # Disk space check
        def check_disk_space():
            import shutil
            total, used, free = shutil.disk_usage("/")
            percent_used = (used / total) * 100
            
            if percent_used > 90:
                return False, f"Disk space critical: {percent_used:.1f}% used", {
                    "total_gb": total / (1024**3),
                    "free_gb": free / (1024**3)
                }
            elif percent_used > 80:
                return True, f"Disk space warning: {percent_used:.1f}% used", {
                    "total_gb": total / (1024**3),
                    "free_gb": free / (1024**3)
                }
            else:
                return True, f"Disk space OK: {percent_used:.1f}% used", {
                    "total_gb": total / (1024**3),
                    "free_gb": free / (1024**3)
                }
        
        self.register_check("disk_space", check_disk_space)
        
        # Memory check
        def check_memory():
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                return False, f"Memory critical: {memory.percent:.1f}% used", {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3)
                }
            elif memory.percent > 80:
                return True, f"Memory warning: {memory.percent:.1f}% used", {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3)
                }
            else:
                return True, f"Memory OK: {memory.percent:.1f}% used", {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3)
                }
        
        self.register_check("memory", check_memory)


from typing import Set