from fastapi import FastAPI

app = FastAPI(title="BotBook")

@app.get("/")
def root():
    return {
        "runtime": "BotBook",
        "status": "running"
    }
