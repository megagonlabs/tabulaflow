import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine.url import make_url
from typing import Literal

# Cache for engines: maps base_url->Engine
_engines = {}
_engines_lock = asyncio.Lock()


async def get_engine_async(
    engine_type: Literal["async", "sync"], url: str, mask_database: bool = False, **engine_kwargs
):
    if mask_database:
        url = make_url(url)._replace(database=None).render_as_string(hide_password=False)

    async with _engines_lock:
        if url not in _engines:
            if engine_type == "async":
                engine = create_async_engine(url, **engine_kwargs)
            else:
                engine = create_engine(url, **engine_kwargs)
            _engines[url] = engine
        return _engines[url]
