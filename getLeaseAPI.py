import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile
from getLeaseInfo import getLeaseInfo
from vectorGenerator import generate_vectors

from typing import List, Dict
import boto3
from botocore.exceptions import NoCredentialsError
import io
from pydantic import BaseModel

app=FastAPI()
app = FastAPI()

s3 = boto3.client('s3')

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
        raise HTTPException(status_code=500, detail=str(e))

# Creating API
@app.post("/generate-vectors")
def generate_vectors_endpoint():
    try:
        generate_vectors()
        return {"status_code": "200"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/uploadFilesToS3/")
def upload_files(files: List[UploadFile] = File(...)):
    for file in files:
        try:
            # Read the file content into a BytesIO object
            file_content = file.file.read()
            file_obj = io.BytesIO(file_content)
            
            # Upload the file to S3
            s3.upload_fileobj(file_obj, 'capleasemanager', f'lease/{file.filename}')
            
            # Generate FAISS index for the newly uploaded file
            generate_and_upload_faiss(file.filename)
            
        except NoCredentialsError:
            raise HTTPException(status_code=403, detail="Credentials not available")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Files uploaded successfully"}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
