from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..schemas.user import UserCreateInternal, UserDelete, UserRead, UserUpdate, UserUpdateInternal

# Create CRUD with explicit type parameters to ensure proper schema mapping
CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdate, UserUpdateInternal, UserDelete, UserRead]
crud_users = CRUDUser(User)

async def create_user_safe(db: AsyncSession, user_data: UserCreateInternal):
    """Create user safely by ensuring init=False fields are not passed to the model."""
    try:
        user_dict = user_data.model_dump(exclude_unset=True)
        user_dict.pop('id', None)
        user_dict.pop('created_at', None)
        
        print(f"[DEBUG] User dict before creation: {user_dict}")
        # Reconstruct schema instance so FastCRUD receives a Pydantic model, not a plain dict
        user_schema = UserCreateInternal(**user_dict)
        created_user = await crud_users.create(db=db, object=user_schema)
        return created_user
    except Exception as e:
        print(f"[ERROR] Failed to create user: {e}")
        print(f"[ERROR] User data: {user_dict}")
        raise