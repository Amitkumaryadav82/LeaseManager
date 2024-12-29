import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from getLeaseInfo import getLeaseInfo
from vectorGenerator import generate_vectors, generate_and_upload_faiss
from typing import List, Dict
import boto3
from botocore.exceptions import NoCredentialsError
import io
from pydantic import BaseModel
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = FastAPI()

s3 = boto3.client('s3')

# Configure logging
logging.basicConfig(filename='fastapi.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Define Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'API request latency', ['method', 'endpoint'])

# Define the logging middleware
class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)
        logging.info(f"Request: {request.method} {request.url} completed in {process_time:.4f} seconds")
        return response

# Add the middleware to the app
app.add_middleware(LogMiddleware)

# Define request and response models
class QueryRequest(BaseModel):
    query: str
    history: List[Dict[str, str]]

class QueryResponse(BaseModel):
    response: str

@app.post("/getLeaseInfo", response_model=QueryResponse)
def invokeGetLeaseInfo(request: QueryRequest):
    try:
        response = getLeaseInfo(request.query, request.history)
        return QueryResponse(response=response)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-vectors")
def generate_vectors_endpoint():
    try:
        generate_vectors()
        return {"status_code": "200"}
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/uploadFilesToS3/")
def upload_files(files: List[UploadFile] = File(...)):
    for file in files:
        try:
            file_content = file.file.read()
            file_obj = io.BytesIO(file_content)
            s3.upload_fileobj(file_obj, 'capleasemanager', f'lease/{file.filename}')
            generate_and_upload_faiss(file.filename)
        except NoCredentialsError:
            raise HTTPException(status_code=403, detail="Credentials not available")
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            file.file.close()
    return {"message": "Files uploaded successfully"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)