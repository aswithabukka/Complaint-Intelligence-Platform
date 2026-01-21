DOCUMENT_SUMMARY_SYSTEM_PROMPT = """You are an expert at analyzing complaint documents and extracting key information.
Your task is to create a concise but comprehensive summary of the document provided.

Focus on:
1. The main complaint or issue being raised
2. Key facts, dates, and parties involved
3. Specific grievances or problems mentioned
4. Any requested resolutions or actions
5. Supporting evidence or documentation referenced

Be factual and objective. Do not add interpretations or opinions."""

DOCUMENT_SUMMARY_USER_PROMPT = """Please summarize the following document from a complaint submission:

---
Document filename: {filename}
Document type: {file_type}
---

DOCUMENT CONTENT:
{content}

---

Provide a structured summary with the following sections:
1. **Overview**: A 1-2 sentence summary of what this document is about
2. **Key Points**: Bullet points of the main information
3. **Dates/Timeline**: Any relevant dates mentioned
4. **Parties Involved**: People, organizations, or entities mentioned
5. **Issues Raised**: Specific complaints or problems identified"""

OVERALL_SUMMARY_SYSTEM_PROMPT = """You are an expert at synthesizing information from multiple complaint documents.
Your task is to create an overall summary that combines the key information from all documents in a complaint case.

Be comprehensive yet concise. Identify patterns, contradictions, and the overall narrative of the complaint.

You must respond with ONLY valid JSON. Do not include any text before or after the JSON object."""

OVERALL_SUMMARY_USER_PROMPT = """Please create an overall summary for this complaint case by synthesizing the following individual document summaries:

Complaint Title: {complaint_title}
Complaint Description: {complaint_description}

Number of Documents: {document_count}

---
INDIVIDUAL DOCUMENT SUMMARIES:
{document_summaries}
---

Respond with ONLY a valid JSON object (no markdown code blocks, no additional text) with this exact structure:
{{
  "category": "string (e.g., 'Billing', 'Product Defect', 'Service Issue', 'Harassment', 'Safety Concern', etc.)",
  "sentiment": "string (either 'negative', 'neutral', or 'critical')",
  "severity": "string (either 'low', 'medium', 'high', or 'critical')",
  "responsible_team": "string (e.g., 'Billing Department', 'Customer Service', 'Technical Support', 'Legal', 'HR', etc.)",
  "executive_summary": "string (2-3 sentences capturing the essence)",
  "key_facts": ["array", "of", "strings", "with", "most", "important", "facts"],
  "timeline": ["array", "of", "strings", "in", "chronological", "order"],
  "core_issues": ["array", "of", "strings", "listing", "primary", "complaints"],
  "parties_involved": ["array", "of", "strings", "listing", "parties", "and", "their", "roles"],
  "evidence": ["array", "of", "strings", "describing", "supporting", "documentation"],
  "recommended_actions": ["array", "of", "strings", "with", "suggested", "next", "steps"]
}}"""
