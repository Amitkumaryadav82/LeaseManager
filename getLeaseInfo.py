import json
import os
import boto3
import tempfile

## LLm Models
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.embeddings import BedrockEmbeddings
from langchain.llms.bedrock import Bedrock

# Vector Embedding And Vector Store
from langchain.vectorstores import FAISS

## Bedrock Clients
bedrock = boto3.client(service_name="bedrock-runtime")
bedrock_embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock)

# S3 client
s3 = boto3.client("s3")

def get_mistral_llm():
    try:
        llm = Bedrock(model_id="mistral.mistral-7b-instruct-v0:2", 
                client=bedrock, model_kwargs={'max_tokens': 200})
        return llm
    except Exception as e:
        print("Exception getting Mistral: {e}")

#  This model is not working as it requires inference profile and I am not able figure it out yet.
def get_llama2_llm():
    try:
        inference_profile_arn = "arn:aws:bedrock:us-east-1:835263753831:inference-profile/us.meta.llama3-2-1b-instruct-v1:0"
        
        llm = Bedrock(model_id="meta.llama3-2-1b-instruct-v1:0", 
                client=bedrock, model_kwargs={'max_gen_len': 512, 
                'inference_profile_arn': inference_profile_arn})
        return llm
    except Exception as e:
        print (" EXCEPTION WHILE GETTING LLM: {e}") 

prompt_template = """
Human: Use the following pieces of context to provide a 
concise answer to the question at the end. If you don't know the answer, 
just say that you don't know, don't try to make up an answer.
<context>
{context}
</context>
Question: {question}
Assistant:
"""

PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

def get_response_llm(llm, vectorstore_faiss, query):
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore_faiss.as_retriever(search_type="similarity", search_kwargs={"k": 3}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    answer = qa({"query": query})
    return answer['result']

def read_faiss_s3(s3_key, bucket_name):
    print("************ inside read_faiss_s3")
    # List objects in the specified S3 bucket and prefix (subdirectory)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_key)
    files = response.get('Contents', [])
    
    # Filter to get the index.faiss and index.pkl files
    faiss_file = next((file['Key'] for file in files if file['Key'].endswith('index.faiss')), None)
    pkl_file = next((file['Key'] for file in files if file['Key'].endswith('index.pkl')), None)
    
    if not faiss_file or not pkl_file:
        raise FileNotFoundError("FAISS index files not found in the specified S3 bucket and prefix.")
    
    # Download the FAISS files to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        faiss_file_path = os.path.join(temp_dir, "index.faiss")
        pkl_file_path = os.path.join(temp_dir, "index.pkl")
        s3.download_file(bucket_name, faiss_file, faiss_file_path)
        s3.download_file(bucket_name, pkl_file, pkl_file_path)
        
        # Verify the files were downloaded correctly
        if not os.path.exists(faiss_file_path) or not os.path.exists(pkl_file_path):
            raise FileNotFoundError(f"FAISS files not found at {faiss_file_path} and {pkl_file_path}")
        
        # Load the FAISS index with dangerous deserialization allowed
        vectorstore_faiss = FAISS.load_local(temp_dir, bedrock_embeddings, allow_dangerous_deserialization=True)
    
    return vectorstore_faiss

def getLeaseInfo(query):
    try:
        llm = get_mistral_llm()  # Create the LLaMA2 model instance
        s3_key = "faiss/"
        s3_bucket = "capleasemanager"
        vectorstore_faiss = read_faiss_s3(s3_key, s3_bucket)
        response = get_response_llm(llm, vectorstore_faiss, query)
        print("Response:", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


