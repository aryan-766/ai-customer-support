"""
FastMCP server for Utility tools (Invoice, Warranty, Email, Calendar).
"""

from fastmcp import FastMCP
from typing import Optional

utility_mcp = FastMCP("Ambrane-Utilities")

@utility_mcp.tool()
async def check_warranty(product_serial: str) -> str:
    """Check the warranty status of a product using its serial number."""
    # Stub implementation
    return f"Warranty for product {product_serial} is valid for 12 more months."

@utility_mcp.tool()
async def get_invoice(order_number: str, email_to: str) -> str:
    """Retrieve an invoice for an order and optionally email it."""
    # Stub implementation
    return f"Invoice for order {order_number} has been generated and sent to {email_to}."

@utility_mcp.tool()
async def send_email(to_address: str, subject: str, body: str) -> str:
    """Send an email to a customer."""
    # Stub implementation
    return f"Email sent successfully to {to_address} with subject '{subject}'."

@utility_mcp.tool()
async def schedule_callback_calendar(customer_name: str, phone: str, time_slot: str) -> str:
    """Schedule a callback in the calendar for a human agent to call the customer."""
    # Stub implementation
    return f"Callback scheduled for {customer_name} ({phone}) at {time_slot}."
