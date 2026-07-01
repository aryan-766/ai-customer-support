"""Tickets API stub."""
from fastapi import APIRouter
router = APIRouter(prefix="/tickets")

@router.get("")
async def list_tickets():
    return {"tickets": []}
