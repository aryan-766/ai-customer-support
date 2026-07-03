"""
FastMCP server for CRM tools.
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any
from app.models import Customer, Order, Ticket
from app.core.database import get_db
from sqlalchemy.future import select

# Create the MCP server for CRM operations
crm_mcp = FastMCP("Ambrane-CRM")

@crm_mcp.tool()
async def crm_lookup(mobile: str) -> Dict[str, Any]:
    """Look up a customer by mobile number."""
    async for session in get_db():
        stmt = select(Customer).where(Customer.mobile == mobile)
        result = await session.execute(stmt)
        customer = result.scalars().first()
        
        if customer:
            return {
                "found": True,
                "id": str(customer.id),
                "name": customer.name,
                "email": customer.email,
                "is_vip": customer.is_vip,
                "crm_id": customer.crm_id
            }
        return {"found": False}

@crm_mcp.tool()
async def check_order_status(customer_id: str, order_number: str) -> str:
    """Check the status of an order for a customer."""
    async for session in get_db():
        stmt = select(Order).where(Order.customer_id == customer_id, Order.order_number == order_number)
        result = await session.execute(stmt)
        order = result.scalars().first()
        
        if order:
            return f"Order {order_number} is currently {order.status}. Total amount: {order.total_amount}"
        return f"Order {order_number} not found for this customer."

@crm_mcp.tool()
async def register_complaint(customer_id: str, subject: str, department: str = "support") -> str:
    """Register a new complaint/ticket for a customer."""
    async for session in get_db():
        ticket = Ticket(
            customer_id=customer_id,
            subject=subject,
            department=department,
            status="open",
            priority="high"
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return f"Complaint registered successfully. Ticket ID: {ticket.id}"

@crm_mcp.tool()
async def register_customer(mobile: str, name: str, email: Optional[str] = None) -> str:
    """Register a new customer."""
    async for session in get_db():
        stmt = select(Customer).where(Customer.mobile == mobile)
        result = await session.execute(stmt)
        if result.scalars().first():
            return "Customer with this mobile number already exists."
            
        customer = Customer(
            mobile=mobile,
            name=name,
            email=email
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
        return f"Customer registered successfully. ID: {customer.id}"
