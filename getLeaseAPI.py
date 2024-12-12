import uvicorn
from fastapi import FastAPI, HTTPException
from getLeaseInfo import getLeaseInfo
from vectorGenerator import generate_vectors


app=FastAPI()

@app.post("/getLeaseInfo")
def invokeGetLeaseInfo(query):
    try:
        response =getLeaseInfo(query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Creating API
@app.post("/generate-vectors")
def generate_vectors_endpoint():
    try:
        generate_vectors()
        return {"status_code": "200"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
