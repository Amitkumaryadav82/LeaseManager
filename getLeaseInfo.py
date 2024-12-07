# This will be lambda which should will invoked for getting responses for the query.

import json
import os
import sys
import boto3
import streamlit as st
import vectorGeneration as vg


## LLm Models
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

## Bedrock Clients
bedrock=boto3.client(service_name="bedrock-runtime")
bedrock_embeddings=BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",client=bedrock)


def get_claude_llm():
    ##create the Anthropic Model
    llm=Bedrock(model_id="ai21.j2-mid-v1",client=bedrock,
                model_kwargs={'maxTokens':512})
    
    return llm

def get_llama2_llm():
    ##create the Anthropic Model
    llm=Bedrock(model_id="meta.llama2-70b-chat-v1",client=bedrock,
                model_kwargs={'max_gen_len':512})
    
    return llm

prompt_template = """

Human: Use the following pieces of context to provide a 
concise answer to the question at the end. If you don't know the answer, 
just say that you don't know, don't try to make up an answer.
<context>
{context}
</context

Question: {question}

Assistant:"""

PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

def get_response_llm(llm,vectorstore_faiss,query):
    qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore_faiss.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
    ),
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT}
)
    answer=qa({"query":query})
    return answer['result']

## This file will contain the code to read the pdf and generate the vectors
## for the generating vector we will be using FAISS and we will store the FAISS files in S3 on AWS

## Data Ingestion

import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader

## We will be suing Titan Embeddings Model To generate Embedding

from langchain_community.embeddings import BedrockEmbeddings
from langchain.llms.bedrock import Bedrock

# Vector Embedding And Vector Store

from langchain.vectorstores import FAISS


bedrock=boto3.client(service_name="bedrock-runtime")
#@TODO Update the model name accordingly
bedrock_embeddings=BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",client=bedrock)



## there may be multiple faiss files int the S3 bucket. We want the lastest ones
def read_faiss_s3(s3_key,s3_bucket):

    # List objects in the specified S3 bucket
    response = s3.list_objects_v2(Bucket=bucket_name)
    files = response.get('Contents', [])
    # Sort files by the LastModified attribute
    files.sort(key=lambda x: x['LastModified'], reverse=True)
    # Get the latest file
    latest_file = files[0]['Key']
    return latest_file
    

# Creating API
@app.post("/get_lease_info")
def get_lease_info(prompt=prompt):
    try:
    #TODO implement this
        return {"status_code": "200"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import unvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ## Since we will using AWS lambda to invoke LLM, we need to write a handler
# def lambda_handler(event, context):
#     # TODO implement body
#     event=json.loads(event['body'])
#     #@TODO: Update the event after the API Gateway configuration
#     query=event['blog_topic']

#     llm= get_claude_llm()
#     #@TODO: Set the S3_Key and S3_Bucket
#     vectorstore_faiss= read_faiss_s3(s3_key,s3_bucket)

#     response=  get_response_llm(llm,vectorstore_faiss,query):

#     if get_response_llm:
#         print("LLM invocation successful")

#     else:
#         print("No blog was generated")

#     return json.dumps(response)

