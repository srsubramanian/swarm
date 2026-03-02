"""Domain-specific tools for deep agent analysis.

Each domain has a list of tools that agents can call during their
internal tool-calling loop to gather evidence before forming assessments.
"""

from app.agents.tools.compliance_tools import COMPLIANCE_TOOLS
from app.agents.tools.engineering_tools import ENGINEERING_TOOLS
from app.agents.tools.security_tools import SECURITY_TOOLS

TOOLS_BY_DOMAIN: dict[str, list] = {
    "compliance": COMPLIANCE_TOOLS,
    "security": SECURITY_TOOLS,
    "engineering": ENGINEERING_TOOLS,
}

__all__ = [
    "COMPLIANCE_TOOLS",
    "SECURITY_TOOLS",
    "ENGINEERING_TOOLS",
    "TOOLS_BY_DOMAIN",
]
