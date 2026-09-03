"""
Prompt templates for all LLM operations.
Centralized for easy tuning and A/B testing.
"""

# ============================================
# RAG Question-Answering
# ============================================

QA_PROMPT = """You are an expert document analyst. Use the provided context to answer the question accurately and thoroughly.
If the context doesn't contain enough information, say so honestly.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


# ============================================
# Document Summarization
# ============================================

SUMMARY_PROMPT = """You are an expert document summarizer. Analyze the following document text and provide a comprehensive summary.

DOCUMENT TEXT:
{text}

Provide your response as a JSON object with these exact keys:
{{
    "executive_summary": "A 2-3 paragraph executive summary",
    "section_summaries": [
        {{"title": "Section title", "summary": "Section summary"}}
    ],
    "bullet_highlights": ["Key highlight 1", "Key highlight 2"],
    "key_takeaways": ["Takeaway 1", "Takeaway 2"]
}}

JSON RESPONSE:"""


# ============================================
# Key Information Extraction
# ============================================

EXTRACTION_LEGAL_PROMPT = """Analyze this legal document and extract key information.

DOCUMENT TEXT:
{text}

Extract and return as JSON:
{{
    "parties": ["Party names involved"],
    "effective_date": "Contract effective date",
    "termination_date": "Contract end date",
    "key_terms": ["Important terms and conditions"],
    "obligations": ["Key obligations for each party"],
    "penalties": ["Penalty clauses"],
    "governing_law": "Applicable law/jurisdiction",
    "special_clauses": ["Notable or unusual clauses"]
}}

JSON RESPONSE:"""


EXTRACTION_FINANCIAL_PROMPT = """Analyze this financial document and extract key metrics.

DOCUMENT TEXT:
{text}

Extract and return as JSON:
{{
    "revenue": "Total revenue figure",
    "expenses": "Total expenses",
    "net_income": "Net income/loss",
    "key_ratios": {{"ratio_name": "value"}},
    "trends": ["Notable financial trends"],
    "risks": ["Financial risk factors"],
    "outlook": "Future outlook summary"
}}

JSON RESPONSE:"""


EXTRACTION_RESEARCH_PROMPT = """Analyze this research paper and extract key information.

DOCUMENT TEXT:
{text}

Extract and return as JSON:
{{
    "methodology": "Research methodology description",
    "key_contributions": ["Main contributions..."],
    "findings": ["Key findings..."],
    "limitations": ["Study limitations..."],
    "future_work": ["Suggested future directions..."],
    "citations_count": "Number of references"
}}

JSON RESPONSE:"""


EXTRACTION_GENERAL_PROMPT = """Analyze this document and extract key information.

DOCUMENT TEXT:
{text}

Extract and return as JSON:
{{
    "main_topics": ["Primary topics covered"],
    "key_points": ["Important points..."],
    "action_items": ["Action items if any..."],
    "references": ["Notable references or citations"]
}}

JSON RESPONSE:"""


# ============================================
# Risk Detection
# ============================================

RISK_DETECTION_PROMPT = """Analyze this document for potential risks, compliance issues, and concerning language.

DOCUMENT TEXT:
{text}

Identify and categorize all risks. Return as JSON:
{{
    "overall_risk_score": "Low|Medium|High",
    "risk_items": [
        {{
            "risk_type": "Compliance|Financial|Legal|Operational|Reputational",
            "severity": "Low|Medium|High",
            "description": "Brief description of the risk",
            "highlighted_text": "Exact quote from document",
            "recommendation": "..."
        }}
    ],
    "total_risks": 0
}}

JSON RESPONSE:"""


# ============================================
# Document Comparison
# ============================================

COMPARISON_PROMPT = """Compare the following documents and identify similarities and differences.

{documents_text}

Provide a structured comparison as JSON:
{{
    "summary": "Overall comparison summary",
    "similarities": ["Similarity 1", "Similarity 2"],
    "differences": [
        {{
            "category": "Category name",
            "document_a": "What Document A says",
            "document_b": "What Document B says",
            "detail": "Detailed explanation"
        }}
    ]
}}

JSON RESPONSE:"""


# ============================================
# Prompt selection helpers
# ============================================

EXTRACTION_PROMPTS = {
    "legal": EXTRACTION_LEGAL_PROMPT,
    "financial": EXTRACTION_FINANCIAL_PROMPT,
    "research": EXTRACTION_RESEARCH_PROMPT,
    "general": EXTRACTION_GENERAL_PROMPT,
}


def get_extraction_prompt(doc_type: str) -> str:
    """Get the extraction prompt template for a given document type."""
    return EXTRACTION_PROMPTS.get(doc_type, EXTRACTION_GENERAL_PROMPT)


# ============================================
# Multi-Document QA
# ============================================

MULTI_DOC_QA_PROMPT = """You are an expert document analyst comparing and answering questions across multiple documents.

DOCUMENTS BEING ANALYZED: {documents}

CONTEXT FROM ALL DOCUMENTS:
{context}

QUESTION: {question}

Instructions:
- Reference specific documents by name when citing information
- If documents disagree, highlight the discrepancy
- If information is only found in one document, note which one
- If no relevant information is found, say so honestly

ANSWER:"""

