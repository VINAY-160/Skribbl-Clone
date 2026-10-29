from fastapi import APIRouter, Query

from app.dependencies import repository

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
async def top_players(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    return await repository.top_players(limit)


@router.get("/matches")
async def recent_matches(limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    return await repository.recent_matches(limit)
