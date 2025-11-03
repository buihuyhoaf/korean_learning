# src/app/api/v1/friends.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException, DuplicateValueException, BadRequestException
from ...models.user import User
from ...models.social import Friend

router = APIRouter(tags=["friends"])


# UC11: Manage Friends
@router.get("/user/{username}/friends", response_model=PaginatedListResponse[dict])
async def get_user_friends(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    status: str = None,  # "accepted", "pending", "blocked"
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's friends list"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own friends")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Build query for friends
    query = db.query(Friend).filter(Friend.user_id == user.id)
    
    if status:
        query = query.filter(Friend.status == status)
    
    query = query.order_by(Friend.created_at.desc())
    
    friends = query.offset(offset).limit(items_per_page).all()
    total = query.count()
    
    friends_data = []
    for friend in friends:
        # Get friend user details
        friend_user = db.query(User).filter(User.id == friend.friend_user_id).first()
        if friend_user:
            friend_dict = {
                "id": friend.id,
                "friend": {
                    "id": friend_user.id,
                    "username": friend_user.username,
                    "exp": friend_user.exp,
                    "streak_days": friend_user.streak_days
                },
                "status": friend.status,
                "created_at": friend.created_at
            }
            friends_data.append(friend_dict)
    
    response = paginated_response(
        crud_data={"data": friends_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/friend-requests", response_model=PaginatedListResponse[dict])
async def get_friend_requests(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    request_type: str = "received",  # "received" or "sent"
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get friend requests (received or sent)"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only view your own friend requests")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    if request_type == "received":
        # Get requests received by user
        query = db.query(Friend).filter(
            Friend.friend_user_id == user.id,
            Friend.status == "pending"
        )
    else:
        # Get requests sent by user
        query = db.query(Friend).filter(
            Friend.user_id == user.id,
            Friend.status == "pending"
        )
    
    query = query.order_by(Friend.created_at.desc())
    
    requests = query.offset(offset).limit(items_per_page).all()
    total = query.count()
    
    requests_data = []
    for request in requests:
        if request_type == "received":
            # Get the user who sent the request
            requester = db.query(User).filter(User.id == request.user_id).first()
            user_info = {
                "id": requester.id,
                "username": requester.username,
                "exp": requester.exp,
                "streak_days": requester.streak_days
            } if requester else None
        else:
            # Get the user who received the request
            receiver = db.query(User).filter(User.id == request.friend_user_id).first()
            user_info = {
                "id": receiver.id,
                "username": receiver.username,
                "exp": receiver.exp,
                "streak_days": receiver.streak_days
            } if receiver else None
        
        if user_info:
            request_dict = {
                "id": request.id,
                "user": user_info,
                "status": request.status,
                "created_at": request.created_at
            }
            requests_data.append(request_dict)
    
    response = paginated_response(
        crud_data={"data": requests_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.post("/user/{username}/friends/send-request", response_model=dict)
async def send_friend_request(
    request: Request,
    username: str,
    friend_username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Send a friend request"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only send friend requests for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    friend_user = db.query(User).filter(User.username == friend_username).first()
    if not friend_user:
        raise NotFoundException("Friend user not found")
    
    if user.id == friend_user.id:
        raise BadRequestException("You cannot send a friend request to yourself")
    
    # Check if friendship already exists
    existing_friendship = db.query(Friend).filter(
        (Friend.user_id == user.id) & (Friend.friend_user_id == friend_user.id) |
        (Friend.user_id == friend_user.id) & (Friend.friend_user_id == user.id)
    ).first()
    
    if existing_friendship:
        if existing_friendship.status == "accepted":
            raise DuplicateValueException("You are already friends with this user")
        elif existing_friendship.status == "pending":
            raise DuplicateValueException("Friend request already exists")
        elif existing_friendship.status == "blocked":
            raise BadRequestException("This user has blocked you")
    
    # Create friend request
    friend_request = Friend(
        user_id=user.id,
        friend_user_id=friend_user.id,
        status="pending"
    )
    db.add(friend_request)
    db.commit()
    
    return {
        "message": f"Friend request sent to {friend_username}",
        "friend_request": {
            "id": friend_request.id,
            "friend_username": friend_username,
            "status": friend_request.status,
            "created_at": friend_request.created_at
        }
    }


@router.put("/user/{username}/friends/{friend_request_id}/accept", response_model=dict)
async def accept_friend_request(
    request: Request,
    username: str,
    friend_request_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Accept a friend request"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only accept friend requests for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    friend_request = db.query(Friend).filter(
        Friend.id == friend_request_id,
        Friend.friend_user_id == user.id,
        Friend.status == "pending"
    ).first()
    
    if not friend_request:
        raise NotFoundException("Friend request not found")
    
    # Update friend request status
    friend_request.status = "accepted"
    
    # Get the requester
    requester = db.query(User).filter(User.id == friend_request.user_id).first()
    
    db.commit()
    
    return {
        "message": f"You are now friends with {requester.username}",
        "friendship": {
            "id": friend_request.id,
            "friend_username": requester.username,
            "status": friend_request.status,
            "accepted_at": friend_request.created_at
        }
    }


@router.put("/user/{username}/friends/{friend_request_id}/reject", response_model=dict)
async def reject_friend_request(
    request: Request,
    username: str,
    friend_request_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Reject a friend request"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only reject friend requests for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    friend_request = db.query(Friend).filter(
        Friend.id == friend_request_id,
        Friend.friend_user_id == user.id,
        Friend.status == "pending"
    ).first()
    
    if not friend_request:
        raise NotFoundException("Friend request not found")
    
    # Delete the friend request
    db.delete(friend_request)
    db.commit()
    
    return {"message": "Friend request rejected"}


@router.put("/user/{username}/friends/{friendship_id}/block", response_model=dict)
async def block_friend(
    request: Request,
    username: str,
    friendship_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Block a friend"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only block friends for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    friendship = db.query(Friend).filter(
        Friend.id == friendship_id,
        (Friend.user_id == user.id) | (Friend.friend_user_id == user.id)
    ).first()
    
    if not friendship:
        raise NotFoundException("Friendship not found")
    
    # Update friendship status to blocked
    friendship.status = "blocked"
    db.commit()
    
    return {"message": "User blocked successfully"}


@router.delete("/user/{username}/friends/{friendship_id}", response_model=dict)
async def remove_friend(
    request: Request,
    username: str,
    friendship_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Remove a friend"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only remove friends for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    friendship = db.query(Friend).filter(
        Friend.id == friendship_id,
        (Friend.user_id == user.id) | (Friend.friend_user_id == user.id)
    ).first()
    
    if not friendship:
        raise NotFoundException("Friendship not found")
    
    # Delete the friendship
    db.delete(friendship)
    db.commit()
    
    return {"message": "Friend removed successfully"}


@router.get("/user/{username}/friends/search", response_model=dict)
async def search_friends(
    request: Request,
    username: str,
    search_query: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Search for users to add as friends"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only search friends for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Search for users by username
    search_query = f"%{search_query}%"
    users_query = db.query(User).filter(
        User.username.ilike(search_query),
        User.id != user.id  # Exclude current user
    ).order_by(User.username)
    
    users = users_query.offset(offset).limit(items_per_page).all()
    total = users_query.count()
    
    # Get existing friendships for current user
    existing_friendships = db.query(Friend).filter(
        (Friend.user_id == user.id) | (Friend.friend_user_id == user.id)
    ).all()
    
    friendship_map = {}
    for friendship in existing_friendships:
        other_user_id = friendship.friend_user_id if friendship.user_id == user.id else friendship.user_id
        friendship_map[other_user_id] = friendship.status
    
    users_data = []
    for found_user in users:
        friendship_status = friendship_map.get(found_user.id, None)
        
        user_dict = {
            "id": found_user.id,
            "username": found_user.username,
            "exp": found_user.exp,
            "streak_days": found_user.streak_days,
            "friendship_status": friendship_status,
            "can_send_request": friendship_status is None
        }
        users_data.append(user_dict)
    
    return {
        "data": users_data,
        "total": total,
        "page": page,
        "items_per_page": items_per_page,
        "total_pages": (total + items_per_page - 1) // items_per_page
    }


@router.get("/user/{username}/friends/stats", response_model=dict)
async def get_friends_stats(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's friends statistics"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own friends stats")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Get friends counts by status
    accepted_friends = db.query(Friend).filter(
        Friend.user_id == user.id,
        Friend.status == "accepted"
    ).count()
    
    pending_sent = db.query(Friend).filter(
        Friend.user_id == user.id,
        Friend.status == "pending"
    ).count()
    
    pending_received = db.query(Friend).filter(
        Friend.friend_user_id == user.id,
        Friend.status == "pending"
    ).count()
    
    blocked_friends = db.query(Friend).filter(
        Friend.user_id == user.id,
        Friend.status == "blocked"
    ).count()
    
    return {
        "accepted_friends": accepted_friends,
        "pending_sent_requests": pending_sent,
        "pending_received_requests": pending_received,
        "blocked_friends": blocked_friends,
        "total_friends": accepted_friends
    }


