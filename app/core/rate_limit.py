"""Single shared slowapi Limiter instance.

Kept separate from app/main.py so routers (app/api/auth.py) can import it
for the @limiter.limit(...) decorator without importing app.main itself,
which would create a circular import (main.py imports the auth router).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
