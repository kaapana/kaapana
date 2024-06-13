from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..schemas import Projects, Data, Rights

from ..database import get_session

router = APIRouter()
