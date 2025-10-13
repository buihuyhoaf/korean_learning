#!/bin/bash
echo "Installing all required dependencies for Korean Learning backend..."

# Core dependencies
pip install crudadmin
pip install asyncpg
pip install uuid6
pip install redis
pip install google-auth
pip install arq
pip install uvicorn
pip install fastapi
pip install sqlalchemy
pip install alembic
pip install python-dotenv
pip install pydantic
pip install python-multipart
pip install python-jose
pip install passlib
pip install bcrypt

echo "All dependencies installed!"
echo "Now you can start the backend with:"
echo "python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload"
