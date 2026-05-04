"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Currently includes tools for web search
and other external integrations.
"""

from langchain_core.tools.base import BaseTool

from .ask_human import ask_human
from .knowledge_base import search_knowledge_base
from .get_order_details import get_order_details

tools: list[BaseTool] = [ask_human, search_knowledge_base, get_order_details]
