from fastapi import HTTPException, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config import config

security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Security(security)) -> str:
    """
    Verify HTTP Basic Authentication credentials

    Args:
        credentials: HTTPBasicCredentials from FastAPI

    Returns:
        Username if authentication successful

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    correct_username = credentials.username == config.AUTH_USERNAME
    correct_password = credentials.password == config.AUTH_PASSWORD

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
