from fastcrud import FastCRUD

from ..models.user import User
from ..schemas.user import UserCreateInternal, UserDelete, UserRead, UserUpdate, UserUpdateInternal, UserModelCreate

CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdate, UserUpdateInternal, UserDelete, UserRead]
crud_users = CRUDUser(User)

# Create a separate CRUD for the actual User model
CRUDUserModel = FastCRUD[User, UserModelCreate, UserUpdate, UserUpdateInternal, UserDelete, UserRead]
crud_user_model = CRUDUserModel(User)
