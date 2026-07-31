from pydantic import BaseModel

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(UserLogin):
    pass

class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool

    class Config:
        from_attributes = True
