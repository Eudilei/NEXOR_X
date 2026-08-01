import asyncio
import uvicorn
from nexor_x.api.app import create_app
from nexor_x.config import get_settings
from nexor_x.kernel import Kernel
from nexor_x.logging import configure_logging

async def serve() -> None:
    settings = get_settings()
    configure_logging(settings.nexor_log_level)
    kernel = Kernel(settings)
    await kernel.start()
    app = create_app(kernel)
    config = uvicorn.Config(
        app=app,
        host=settings.nexor_host,
        port=settings.nexor_port,
        log_level=settings.nexor_log_level.lower(),
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        await kernel.stop()

def run() -> None:
    asyncio.run(serve())

if __name__ == "__main__":
    run()
