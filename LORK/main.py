# Entrypoint for Vercel deployment
from lork.api_server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
