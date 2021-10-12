import sys
from apihub.server import ServerSettings, api, metrics_router


def main():
    import uvicorn

    settings = ServerSettings()
    settings.parse_args(args=sys.argv)

    if settings.monitoring:
        api.include_router(metrics_router)

    uvicorn.run(
        "run_server:api",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.reload,
        debug=settings.debug,
    )


if __name__ == "__main__":
    main()
