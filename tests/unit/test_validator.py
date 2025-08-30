"""Unit tests for zero-hallucination validator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.query.validator import ZeroHallucinationValidator, ValidationResult


@pytest.fixture
def validator():
    """Create validator for testing."""
    return ZeroHallucinationValidator(confidence_threshold=0.7)


@pytest.mark.asyncio
async def test_validation_with_high_confidence(validator):
    """Test validation with high confidence score."""
    response = {"data": {"ip": "192.168.1.1"}}
    source_ids = ["entity-1", "entity-2"]
    scores = [0.9, 0.85]
    
    with patch.object(validator, '_verify_sources') as mock_verify:
        mock_verify.return_value = [
            {"id": "entity-1", "name": "Router 1"},
            {"id": "entity-2", "name": "Router 2"}
        ]
        
        with patch.object(validator, '_validate_content') as mock_validate:
            mock_validate.return_value = True
            
            result = await validator.validate_response(
                response=response,
                source_ids=source_ids,
                similarity_scores=scores
            )
    
    assert result.valid is True
    assert result.confidence == 0.875  # Average of scores
    assert result.source_ids == source_ids
    assert result.response == response


@pytest.mark.asyncio
async def test_validation_with_low_confidence(validator):
    """Test validation with low confidence score."""
    response = {"data": {"ip": "192.168.1.1"}}
    source_ids = ["entity-1"]
    scores = [0.5]  # Below threshold
    
    result = await validator.validate_response(
        response=response,
        source_ids=source_ids,
        similarity_scores=scores
    )
    
    assert result.valid is False
    assert result.confidence == 0.5
    assert "below threshold" in result.message


@pytest.mark.asyncio
async def test_validation_without_sources(validator):
    """Test validation without source documents."""
    response = {"data": {"ip": "192.168.1.1"}}
    
    result = await validator.validate_response(
        response=response,
        source_ids=[],
        similarity_scores=[]
    )
    
    assert result.valid is False
    assert result.confidence == 0.0
    assert "No source documents" in result.message


@pytest.mark.asyncio
async def test_validation_with_missing_sources(validator):
    """Test validation when source documents don't exist."""
    response = {"data": {"ip": "192.168.1.1"}}
    source_ids = ["entity-1", "entity-2"]
    scores = [0.9, 0.85]
    
    with patch.object(validator, '_verify_sources') as mock_verify:
        # Return fewer documents than requested
        mock_verify.return_value = [
            {"id": "entity-1", "name": "Router 1"}
        ]
        
        result = await validator.validate_response(
            response=response,
            source_ids=source_ids,
            similarity_scores=scores
        )
    
    assert result.valid is False
    assert "source documents not found" in result.message


@pytest.mark.asyncio
async def test_content_validation_success(validator):
    """Test successful content validation."""
    response = {
        "data": {
            "ip": "192.168.1.1",
            "hostname": "router.local"
        }
    }
    
    source_documents = [
        {
            "id": "entity-1",
            "attributes": {
                "ip": "192.168.1.1",
                "hostname": "router.local"
            }
        }
    ]
    
    result = await validator._validate_content(response, source_documents)
    assert result is True


@pytest.mark.asyncio
async def test_content_validation_failure(validator):
    """Test failed content validation."""
    response = {
        "data": {
            "ip": "10.0.0.1",  # Different from source
            "hostname": "router.local"
        }
    }
    
    source_documents = [
        {
            "id": "entity-1",
            "attributes": {
                "ip": "192.168.1.1",
                "hostname": "router.local"
            }
        }
    ]
    
    # Mock claim verification to return False for mismatched data
    with patch.object(validator, '_verify_claim') as mock_verify:
        mock_verify.side_effect = [False, True]  # First claim fails
        
        result = await validator._validate_content(response, source_documents)
        
    assert result is False


@pytest.mark.asyncio
async def test_extract_claims_from_dict():
    """Test claim extraction from dictionary response."""
    validator_inst = ZeroHallucinationValidator()
    
    response = {
        "data": {
            "ip": "192.168.1.1",
            "hostname": "router.local",
            "status": "active"
        }
    }
    
    claims = validator_inst._extract_claims(response)
    
    assert len(claims) == 3
    assert claims[0]["type"] == "attribute"
    assert claims[0]["key"] == "ip"
    assert claims[0]["value"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_extract_claims_from_list():
    """Test claim extraction from list response."""
    validator_inst = ZeroHallucinationValidator()
    
    response = {
        "data": [
            {"id": "1", "name": "Router 1"},
            {"id": "2", "name": "Router 2"}
        ]
    }
    
    claims = validator_inst._extract_claims(response)
    
    assert len(claims) == 2
    assert claims[0]["type"] == "entity"
    assert claims[0]["data"]["id"] == "1"


@pytest.mark.asyncio
async def test_verify_attribute_claim():
    """Test verification of attribute claims."""
    validator_inst = ZeroHallucinationValidator()
    
    claim = {
        "type": "attribute",
        "key": "ip",
        "value": "192.168.1.1"
    }
    
    source_documents = [
        {
            "attributes": {
                "ip": "192.168.1.1",
                "hostname": "router.local"
            }
        }
    ]
    
    result = validator_inst._verify_claim(claim, source_documents)
    assert result is True
    
    # Test with non-matching value
    claim["value"] = "10.0.0.1"
    result = validator_inst._verify_claim(claim, source_documents)
    assert result is False


@pytest.mark.asyncio
async def test_verify_entity_claim():
    """Test verification of entity claims."""
    validator_inst = ZeroHallucinationValidator()
    
    claim = {
        "type": "entity",
        "data": {"id": "entity-1"}
    }
    
    source_documents = [
        {"id": "entity-1", "name": "Router 1"},
        {"id": "entity-2", "name": "Router 2"}
    ]
    
    result = validator_inst._verify_claim(claim, source_documents)
    assert result is True
    
    # Test with non-existing entity
    claim["data"]["id"] = "entity-3"
    result = validator_inst._verify_claim(claim, source_documents)
    assert result is False


@pytest.mark.asyncio
async def test_create_safe_response():
    """Test safe response creation."""
    validator_inst = ZeroHallucinationValidator()
    
    response = validator_inst.create_safe_response(
        query="What's the router IP?",
        reason="No matching data found"
    )
    
    assert response["success"] is False
    assert response["query"] == "What's the router IP?"
    assert response["message"] == "No matching data found"
    assert response["data"] is None
    assert response["confidence"] == 0.0
    assert response["source_ids"] == []


@pytest.mark.asyncio
async def test_batch_validation():
    """Test batch validation of responses."""
    validator_inst = ZeroHallucinationValidator(confidence_threshold=0.7)
    
    responses = [
        {
            "response": {"data": {"ip": "192.168.1.1"}},
            "source_ids": ["entity-1"],
            "scores": [0.9]
        },
        {
            "response": {"data": {"ip": "10.0.0.1"}},
            "source_ids": ["entity-2"],
            "scores": [0.5]  # Below threshold
        },
        {
            "response": {"data": {"ip": "172.16.0.1"}},
            "source_ids": [],  # No sources
            "scores": []
        }
    ]
    
    with patch.object(validator_inst, '_verify_sources') as mock_verify:
        mock_verify.return_value = [{"id": "entity-1"}]
        
        with patch.object(validator_inst, '_validate_content') as mock_validate:
            mock_validate.return_value = True
            
            results = await validator_inst.validate_batch(responses)
    
    assert len(results) == 3
    assert results[0].valid is True
    assert results[1].valid is False  # Low confidence
    assert results[2].valid is False  # No sources