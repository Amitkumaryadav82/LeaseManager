## This will be a separate lambda which will be used to generate the vectors

import numpy as np
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.vectorstores import FAISS
from langchain.schema import Document
from io import BytesIO
import boto3
import os
import pytesseract
from PIL import Image
from langchain_community.embeddings import BedrockEmbeddings
import datetime
from fastapi import FastAPI, HTTPException
import uvicorn
from logger import getLogger
from concurrent.futures import ThreadPoolExecutor


log=getLogger()

setting = {}
with open('settings.txt', 'r') as file:
    for line in file:
        if line.strip():  # Ignore empty lines
            key, value = line.strip().split('=')
            setting[key] = value

print(setting)

bucket_name = 'capleasemanager'
prefix = 'lease/'
s3_faiss='faiss/'
bedrock=boto3.client(service_name="bedrock-runtime")
bedrock_embeddings=BedrockEmbeddings(model_id=setting.get('embedding_model'),client=bedrock)
# app=FastAPI()

#Get the documents
def get_documents_from_s3(s3_bucket, prefix):
    log.info("Starting to retrieve documents from S3")

    s3 = boto3.client("s3")
    paginator = s3.get_paginator('list_objects_v2')
    text_list = []

    def process_file(file_key):
        if file_key.endswith('.png'):
            obj = s3.get_object(Bucket=s3_bucket, Key=file_key)
            img_data = obj['Body'].read()
            image = Image.open(BytesIO(img_data))
            text = pytesseract.image_to_string(image)
            return text

    for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
        files = page.get('Contents', [])
        with ThreadPoolExecutor() as executor:
            results = executor.map(lambda file: process_file(file['Key']), files)
            text_list.extend(results)

    log.info("Completed retrieving documents from S3")
    return text_list


# read the texts from the documents
def read_text_from_files(pngfiles):
    log.info("Starting to read text from files")
    text_list = []
    folder_path = 'testdata/'
    for filename in os.listdir(folder_path):
        if filename.endswith('.png'):
            img_path = os.path.join(folder_path, filename)
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            text_list.append(text)
    log.info("Successfully read text from files")
    return text_list

## This function will read the data and  split the documents into chunk
def data_splitter(documents):
    log.info("Starting to split documents")

    text_splitter=RecursiveCharacterTextSplitter(chunk_size=10000,
                                                 chunk_overlap=1000)
    split_texts=[]
    for doc in documents:

        chunk=text_splitter.split_text(doc)
        split_texts.extend(chunk)
    log.info("Completed split documents")
    return split_texts

   # Generate the FAISS vectors from the documents
def generate_faiss(split_docs):
    log.info("Starting to generate fiass")
    documents = [Document(page_content=text) for text in split_docs]
    vectorstore_faiss = FAISS.from_documents(
        documents,
        bedrock_embeddings  
    )
    log.info("Completed:generate fiass")
    return vectorstore_faiss

# Save the generated FAISS vectors in S3

def save_faiss_s3(faiss_index):
    log.info("Starting to save fiass in s3")
    s3 = boto3.client('s3')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = f'/tmp/faiss_index_{timestamp}'  # Use a unique directory name with timestamp

    # Ensure the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save the FAISS index to the local directory
    faiss_index.save_local(directory)  # Save to the directory

    # Read the local files and upload them to S3
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        with open(file_path, 'rb') as f:
            s3.put_object(Bucket=bucket_name, Key=s3_faiss + file, Body=f.read())

    log.info("FAISS index saved to S3 from directory {directory}")


def generate_vectors():
    log.info("Starting to generate Vectors")
    list_text = get_documents_from_s3(bucket_name,prefix)
    # list_text=read_text_from_files(raw_png)
    splitted_text= data_splitter(list_text)
    vectorstore_faiss= generate_faiss(splitted_text)
    save_faiss_s3(vectorstore_faiss)
    log.info("Finished Generating Vectors")

if __name__== "__main__":
   generate_vectors()