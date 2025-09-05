#!/usr/bin/env python3
"""Import markdown documents directly into the database for Faucets."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging
import hashlib

sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample markdown documents for Faucets
# You can replace these with your actual markdown content
SAMPLE_DOCUMENTS = [
    {
        "name": "Faucets Company Overview",
        "content": """# Faucets Limited - Company Overview

## About Faucets
Faucets Limited is a leading provider of premium plumbing fixtures and bathroom fittings. Established in 1985, we have been serving residential and commercial clients for nearly four decades.

## Mission Statement
To provide innovative, high-quality plumbing solutions that combine functionality with aesthetic appeal, while maintaining our commitment to sustainability and customer satisfaction.

## Core Services
- Premium bathroom fixtures
- Commercial plumbing solutions
- Custom design services
- Installation and maintenance
- Water conservation systems

## Key Locations
- Head Office: London, UK
- Manufacturing: Birmingham, UK
- Distribution Centers: Manchester, Glasgow, Bristol

## Contact Information
- Phone: +44 20 7946 0958
- Email: info@faucets.co.uk
- Website: www.faucets.co.uk
""",
        "tags": ["company", "overview", "about"]
    },
    {
        "name": "IT Infrastructure Documentation",
        "content": """# IT Infrastructure Documentation

## Network Architecture
Our network infrastructure consists of multiple interconnected components designed for high availability and security.

### Core Components
1. **Firewalls**
   - Sophos XGS Firewall (Primary)
   - Redundant failover configuration
   
2. **Switches**
   - Aruba 48 Port Switch (Core)
   - HP V1810-48G Switches (Distribution)
   
3. **Servers**
   - FCLHYPERV01 - Virtualization Host
   - SQL Server - Database Server
   - DCFP01 - Domain Controller

### Network Topology
```
Internet --> Firewall --> Core Switch --> Distribution Switches --> End Devices
                |              |
                v              v
              DMZ          Server Farm
```

## Security Measures
- Multi-factor authentication
- Network segmentation
- Regular security audits
- Encrypted communications
- Backup and disaster recovery

## Monitoring
- 24/7 network monitoring
- Performance metrics tracking
- Alert system for critical events
""",
        "tags": ["infrastructure", "network", "documentation"]
    },
    {
        "name": "Standard Operating Procedures",
        "content": """# Standard Operating Procedures (SOPs)

## Daily Operations

### Morning Startup Procedures
1. Check system status dashboard
2. Review overnight alerts and logs
3. Verify backup completion
4. Test critical services
5. Update status board

### Incident Response
1. **Initial Assessment**
   - Identify affected systems
   - Determine severity level
   - Notify stakeholders

2. **Containment**
   - Isolate affected systems
   - Prevent spread of issue
   - Document findings

3. **Resolution**
   - Apply fixes
   - Test solutions
   - Verify normal operations

4. **Post-Incident**
   - Root cause analysis
   - Update documentation
   - Implement preventive measures

## Maintenance Windows
- **Regular Maintenance**: Every Sunday 2:00 AM - 6:00 AM
- **Emergency Maintenance**: As required with 2-hour notice
- **Major Updates**: Quarterly, scheduled 30 days in advance

## Change Management
All changes must go through:
1. Change request submission
2. Impact assessment
3. Approval process
4. Implementation planning
5. Testing and validation
6. Documentation update
""",
        "tags": ["procedures", "operations", "sop"]
    },
    {
        "name": "Security Policies and Compliance",
        "content": """# Security Policies and Compliance

## Information Security Policy

### Purpose
This policy establishes the framework for information security at Faucets Limited, ensuring the confidentiality, integrity, and availability of our data and systems.

### Scope
This policy applies to all employees, contractors, and third parties with access to Faucets Limited information systems.

## Access Control
- **Principle of Least Privilege**: Users receive minimum access required
- **Multi-Factor Authentication**: Required for all administrative access
- **Password Policy**:
  - Minimum 12 characters
  - Complexity requirements enforced
  - 90-day rotation
  - No password reuse for 12 cycles

## Data Classification
1. **Public**: Information intended for public release
2. **Internal**: General business information
3. **Confidential**: Sensitive business data
4. **Restricted**: Highly sensitive data requiring special handling

## Compliance Requirements
- **GDPR**: Full compliance with data protection regulations
- **ISO 27001**: Information security management standards
- **PCI DSS**: Payment card industry standards (where applicable)

## Security Incident Management
- Immediate reporting of security incidents
- Defined escalation procedures
- Forensic investigation capabilities
- Breach notification procedures

## Regular Audits
- Quarterly vulnerability assessments
- Annual penetration testing
- Compliance audits
- Security awareness training
""",
        "tags": ["security", "compliance", "policy"]
    },
    {
        "name": "Disaster Recovery Plan",
        "content": """# Disaster Recovery Plan

## Executive Summary
This document outlines Faucets Limited's disaster recovery procedures to ensure business continuity in the event of a major incident.

## Recovery Objectives
- **RTO (Recovery Time Objective)**: 4 hours for critical systems
- **RPO (Recovery Point Objective)**: 1 hour maximum data loss

## Critical Systems Priority
### Tier 1 (0-2 hours)
- Email and communications
- Core database servers
- Authentication services

### Tier 2 (2-4 hours)
- File servers
- Application servers
- Customer-facing websites

### Tier 3 (4-8 hours)
- Development environments
- Non-critical applications
- Archive systems

## Backup Strategy
- **Daily Incremental Backups**: Retained for 30 days
- **Weekly Full Backups**: Retained for 12 weeks
- **Monthly Archives**: Retained for 7 years
- **Offsite Replication**: Real-time to secondary datacenter
- **Cloud Backup**: AWS S3 with versioning enabled

## Emergency Contacts
| Role | Primary | Secondary |
|------|---------|-----------|
| IT Manager | John Smith +44 7700 900123 | Jane Doe +44 7700 900456 |
| Network Admin | Bob Wilson +44 7700 900789 | Alice Brown +44 7700 900321 |
| Security Lead | Charlie Davis +44 7700 900654 | Diana Miller +44 7700 900987 |

## Testing Schedule
- Monthly: Backup restoration tests
- Quarterly: Failover testing
- Annually: Full disaster recovery simulation

## Recovery Procedures
1. Assess the situation and activate DR team
2. Establish command center
3. Begin recovery operations per priority
4. Communicate status to stakeholders
5. Document all actions taken
6. Conduct post-incident review
""",
        "tags": ["disaster-recovery", "backup", "business-continuity"]
    }
]


async def import_markdown_documents():
    """Import markdown documents into the database."""
    
    print("=" * 80)
    print("IMPORTING MARKDOWN DOCUMENTS FOR FAUCETS")
    print("=" * 80)
    
    await db_manager.initialize()
    
    org_id = "3183713165639879"  # Faucets organization ID
    documents_imported = 0
    
    async with db_manager.get_session() as session:
        uow = UnitOfWork(session)
        
        for idx, doc_data in enumerate(SAMPLE_DOCUMENTS, 1):
            # Generate a unique document ID based on content hash
            content_hash = hashlib.md5(doc_data['content'].encode()).hexdigest()
            doc_id = f"doc_{content_hash[:16]}"
            
            print(f"\n📄 Document {idx}: {doc_data['name']}")
            print("-" * 40)
            
            # Build searchable text
            search_text = f"{doc_data['name']} {doc_data['content']}".lower()
            
            # Create attributes similar to IT Glue document structure
            attributes = {
                "name": doc_data['name'],
                "content": doc_data['content'],
                "content-type": "text/markdown",
                "parsed-content": doc_data['content'],  # For markdown, parsed = raw
                "created-at": datetime.utcnow().isoformat(),
                "updated-at": datetime.utcnow().isoformat(),
                "tags": doc_data.get('tags', []),
                "source": "markdown_import",
                "word_count": len(doc_data['content'].split()),
                "character_count": len(doc_data['content'])
            }
            
            # Create entity
            entity = ITGlueEntity(
                itglue_id=doc_id,
                entity_type='document',
                organization_id=org_id,
                name=doc_data['name'],
                attributes=attributes,
                relationships={},
                search_text=search_text,
                last_synced=datetime.utcnow()
            )
            
            # Check if document exists
            existing = await uow.itglue.get_by_itglue_id(doc_id)
            if existing:
                # Update existing
                for key, value in entity.__dict__.items():
                    if not key.startswith('_'):
                        setattr(existing, key, value)
            else:
                # Create new
                session.add(entity)
            
            print(f"  ✓ Document ID: {doc_id}")
            print(f"  ✓ Content length: {len(doc_data['content']):,} chars")
            print(f"  ✓ Word count: {attributes['word_count']:,}")
            print(f"  ✓ Tags: {', '.join(doc_data.get('tags', []))}")
            
            documents_imported += 1
        
        await session.commit()
        print(f"\n✅ Imported {documents_imported} documents")
    
    # Verify import
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    async with db_manager.get_session() as session:
        from sqlalchemy import text
        
        result = await session.execute(text("""
            SELECT 
                name,
                itglue_id,
                attributes->>'word_count' as word_count,
                attributes->'tags' as tags
            FROM itglue_entities
            WHERE organization_id = :org_id
            AND entity_type = 'document'
            ORDER BY name
        """), {"org_id": org_id})
        
        docs = result.fetchall()
        
        print(f"\n📚 Documents in database: {len(docs)}")
        print("-" * 40)
        
        for doc in docs:
            tags = doc.tags if doc.tags else []
            print(f"\n📄 {doc.name}")
            print(f"   ID: {doc.itglue_id}")
            print(f"   Words: {doc.word_count}")
            if isinstance(tags, list):
                print(f"   Tags: {', '.join(tags)}")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
The 5 markdown documents have been imported successfully!

Now you can:
1. Generate embeddings for semantic search
2. Update Neo4j graph with document relationships
3. Test unified search across all documents

To search these documents:
- Use keyword search for specific terms
- Use semantic search for concepts
- Use graph search for relationships

Example searches to try:
- "network infrastructure"
- "security policy"
- "disaster recovery"
- "backup procedures"
- "compliance requirements"
""")


if __name__ == "__main__":
    print("""
This script will import 5 sample markdown documents for Faucets.
If you have your own markdown files, you can modify the SAMPLE_DOCUMENTS
list in this script to use your actual content.

Press Enter to proceed with sample documents, or Ctrl+C to cancel...
""")
    input()
    
    asyncio.run(import_markdown_documents())