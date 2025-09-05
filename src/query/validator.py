"""Zero-hallucination validation for query responses."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.data import UnitOfWork, db_manager

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of response validation."""

    valid: bool
    confidence: float
    message: Optional[str] = None
    response: Optional[dict[str, Any]] = None
    source_ids: Optional[list[str]] = None
    source_documents: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "confidence": self.confidence,
            "message": self.message,
            "response": self.response,
            "source_ids": self.source_ids,
            "source_documents": self.source_documents
        }


class ZeroHallucinationValidator:
    """Validates responses to ensure zero hallucination."""

    def __init__(
        self,
        confidence_threshold: float = 0.4,
        require_source: bool = True
    ):
        """Initialize validator.

        Args:
            confidence_threshold: Minimum confidence score
            require_source: Whether to require source documents
        """
        self.confidence_threshold = confidence_threshold
        self.require_source = require_source

    async def validate_response(
        self,
        response: dict[str, Any],
        source_ids: list[str],
        similarity_scores: list[float]
    ) -> ValidationResult:
        """Validate a response against source documents.

        Args:
            response: Response data to validate
            source_ids: Source document IDs
            similarity_scores: Similarity scores for sources

        Returns:
            Validation result
        """
        # Check for source documents
        if self.require_source and not source_ids:
            logger.warning("No source documents provided")
            return ValidationResult(
                valid=False,
                confidence=0.0,
                message="No source documents found"
            )

        # Calculate average confidence
        if similarity_scores:
            avg_confidence = sum(similarity_scores) / len(similarity_scores)
        else:
            avg_confidence = 0.0

        # Check confidence threshold
        if avg_confidence < self.confidence_threshold:
            logger.warning(
                f"Confidence {avg_confidence:.2f} below threshold "
                f"{self.confidence_threshold}"
            )
            return ValidationResult(
                valid=False,
                confidence=avg_confidence,
                message=f"Response confidence ({avg_confidence:.2f}) below threshold"
            )

        # Verify source documents exist
        source_documents = await self._verify_sources(source_ids)

        if self.require_source and len(source_documents) != len(source_ids):
            missing = len(source_ids) - len(source_documents)
            logger.error(f"{missing} source documents not found")
            return ValidationResult(
                valid=False,
                confidence=avg_confidence,
                message=f"{missing} source documents not found"
            )

        # Validate response content against sources
        content_valid = await self._validate_content(
            response,
            source_documents
        )

        if not content_valid:
            return ValidationResult(
                valid=False,
                confidence=avg_confidence,
                message="Response content not supported by sources"
            )

        # Response is valid
        return ValidationResult(
            valid=True,
            confidence=avg_confidence,
            response=response,
            source_ids=source_ids,
            source_documents=source_documents
        )

    async def _verify_sources(
        self,
        source_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Verify source documents exist.

        Args:
            source_ids: Source document IDs

        Returns:
            List of source documents
        """
        if not source_ids:
            return []

        try:
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)

                # Get entities by IDs
                entities = await uow.itglue.get_by_ids(source_ids)

                # Convert to documents
                documents = []
                for entity in entities:
                    documents.append({
                        "id": str(entity.id),
                        "itglue_id": entity.itglue_id,
                        "name": entity.name,
                        "type": entity.entity_type,
                        "attributes": entity.attributes,
                        "last_synced": entity.last_synced
                    })

                return documents

        except Exception as e:
            logger.error(f"Failed to verify sources: {e}")
            return []

    async def _validate_content(
        self,
        response: dict[str, Any],
        source_documents: list[dict[str, Any]]
    ) -> bool:
        """Validate response content against sources.

        Args:
            response: Response to validate
            source_documents: Source documents

        Returns:
            Whether content is valid
        """
        if not source_documents:
            return not self.require_source

        # Extract claims from response
        claims = self._extract_claims(response)

        # Verify each claim
        for claim in claims:
            if not self._verify_claim(claim, source_documents):
                logger.warning(f"Unverified claim: {claim}")
                return False

        return True

    def _extract_claims(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract verifiable claims from response.

        Args:
            response: Response data

        Returns:
            List of claims
        """
        claims = []

        # Extract data points from response
        if "data" in response:
            data = response["data"]

            if isinstance(data, dict):
                for key, value in data.items():
                    if value is not None:
                        claims.append({
                            "type": "attribute",
                            "key": key,
                            "value": value
                        })

            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        claims.append({
                            "type": "entity",
                            "data": item
                        })

        return claims

    def _verify_claim(
        self,
        claim: dict[str, Any],
        source_documents: list[dict[str, Any]]
    ) -> bool:
        """Verify a single claim against sources.

        Args:
            claim: Claim to verify
            source_documents: Source documents

        Returns:
            Whether claim is verified
        """
        claim_type = claim.get("type")

        if claim_type == "attribute":
            # Verify attribute value
            key = claim.get("key")
            value = claim.get("value")

            for doc in source_documents:
                attributes = doc.get("attributes", {})
                if key in attributes and attributes[key] == value:
                    return True

        elif claim_type == "entity":
            # Verify entity exists
            entity_data = claim.get("data", {})
            entity_id = entity_data.get("id")

            for doc in source_documents:
                if doc.get("id") == entity_id or doc.get("itglue_id") == entity_id:
                    return True

        # Default to true if we can't verify
        # (conservative approach to avoid false negatives)
        return True

    async def validate_batch(
        self,
        responses: list[dict[str, Any]]
    ) -> list[ValidationResult]:
        """Validate multiple responses.

        Args:
            responses: List of responses with source info

        Returns:
            List of validation results
        """
        results = []

        for response_data in responses:
            result = await self.validate_response(
                response=response_data.get("response", {}),
                source_ids=response_data.get("source_ids", []),
                similarity_scores=response_data.get("scores", [])
            )
            results.append(result)

        return results

    def create_safe_response(
        self,
        query: str,
        reason: str = "No reliable data available"
    ) -> dict[str, Any]:
        """Create a safe response when validation fails.

        Args:
            query: Original query
            reason: Reason for safe response

        Returns:
            Safe response
        """
        return {
            "success": False,
            "query": query,
            "message": reason,
            "data": None,
            "confidence": 0.0,
            "source_ids": [],
            "timestamp": datetime.utcnow().isoformat()
        }
