import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

port = int(os.getenv("PORT", 8081))  

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
