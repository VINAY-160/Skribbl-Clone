from fastapi import APIRouter, HTTPException

from app.dependencies import registry
from app.schemas.room import CreateRoomRequest, CreateRoomResponse, RoomInfo

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=CreateRoomResponse, status_code=201)
async def create_room(body: CreateRoomRequest) -> CreateRoomResponse:
    """Create a room. The creator then opens /ws/{room_id}?name=... and becomes host."""
    room = registry.create(body.settings)
    return CreateRoomResponse(room_id=room.id, is_private=room.settings.is_private,
                              ws_path=f"/ws/{room.id}")


@router.get("", response_model=list[RoomInfo])
async def list_public_rooms() -> list[dict]:
    return [r.info() for r in registry.list_public()]


@router.get("/{room_id}", response_model=RoomInfo)
async def get_room(room_id: str) -> dict:
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room.info()
