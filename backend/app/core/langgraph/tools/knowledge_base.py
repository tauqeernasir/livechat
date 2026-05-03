"""Knowledge base search tool for LangGraph."""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.services.knowledge.service import knowledge_service
from app.services.database import database_service
from app.core.logging import logger

@tool
async def search_knowledge_base(query: str, config: RunnableConfig) -> str:
    """Search the business knowledge base for information about products, policies, or FAQs.
    
    Use this tool whenever you need accurate, business-specific information to answer a user's question.
    The results will include text snippets and their source filenames.
    """
    workspace_id = config.get("metadata", {}).get("workspace_id")
    
    if not workspace_id:
        logger.error("workspace_id_missing_in_tool_config")
        return "Error: Workspace ID not found. Ensure you are within a workspace context."
    
    try:
        async with database_service.async_session_maker() as session:
            results = await knowledge_service.retrieve_relevant_chunks(
                session=session,
                workspace_id=workspace_id,
                query=query,
                k=4
            )
        
        if not results:
            return "No relevant information found in the knowledge base. Please try rephrasing or check if documents are uploaded."
        
        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(f"--- Result {i} (Source: {res['source']}) ---\n{res['text']}")
        
        logger.info("knowledge_base_search_completed", workspace_id=workspace_id, query=query, results_count=len(results))
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.exception("knowledge_base_tool_failed", error=str(e))
        return f"Error occurred while searching the knowledge base: {str(e)}"
