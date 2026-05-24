"""Authentication routes."""
from fastapi import APIRouter

router = APIRouter()


@router.post("/register")
async def register():
    return {"message": "register endpoint"}


@router.post("/login")
async def login():
    return {"message": "login endpoint"}


@router.get("/me")
async def get_me():
    return {"message": "get current user"}
