"""Knowledge base search tool for LangGraph."""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.services.knowledge.service import knowledge_service
from app.services.database import database_service
from app.core.logging import logger

# TODO: implement actual order details fetching logic
@tool
async def get_order_details(order_num: str, config: RunnableConfig) -> str:
    """Search the users order/service details by order number.
    
    Use this tool whenever you need exact details for an order or service. It should return the specific information related to the order number provided in the query, such as order status, items, delivery date, etc.
    If the query does not contain a valid order number, return an error message indicating that the order number is missing or invalid.
    """
    workspace_id = config.get("metadata", {}).get("workspace_id")
    
    if not workspace_id:
        logger.error("workspace_id_missing_in_tool_config")
        return "Error: Workspace ID not found. Ensure you are within a workspace context."
    
    if order_num == "12345":
        return "Order 12345: Status: Shipped, Items: Widget A, Widget B, Delivery Date: 2024-06-30"
    else:
        return f"No details found for order number {order_num}. Please check the order number and try again."