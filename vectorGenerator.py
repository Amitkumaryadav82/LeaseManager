import boto3
import logging
from PIL import Image
from io import BytesIO
import pytesseract
from concurrent.futures import ThreadPoolExecutor
import datetime
import os
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain_community.embeddings import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from logger import getLogger

log = getLogger()

setting = {}
with open('settings.txt', 'r') as file:
    for line in file:
        if line.strip():  # Ignore empty lines
            key, value = line.strip().split('=')
            setting[key] = value

print(setting)

bucket_name = 'capleasemanager'
prefix = 'lease/'
s3_faiss = 'faiss/'
bedrock = boto3.client(service_name="bedrock-runtime")
bedrock_embeddings = BedrockEmbeddings(model_id=setting.get('embedding_model'), client=bedrock)

def process_file(s3_client, bucket, file_key):
    log.info(f"Calling process_file for {file_key}")
    try:
        if file_key.endswith('.png'):
            obj = s3_client.get_object(Bucket=bucket, Key=file_key)
            img_data = obj['Body'].read()
            image = Image.open(BytesIO(img_data))
            
            # Set a valid resolution if it's invalid
            if image.info.get('dpi') is None or image.info['dpi'] == (0, 0):
                image.info['dpi'] = (300, 300)
            
            text = pytesseract.image_to_string(image)
            return text
    except Exception as e:
        log.error(f"Error processing file {file_key}: {e}")
        return None

def get_documents_from_s3_in_batches(s3_bucket, prefix, batch_size=100):
    log.info("Calling get_documents_from_s3_in_batches")
    log.info("Starting to retrieve documents from S3 in batches")

    s3 = boto3.client("s3")
    paginator = s3.get_paginator('list_objects_v2')
    text_list = []
    batch = []
    batch_number = 0

    try:
        for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
            files = page.get('Contents', [])
            for file in files:
                batch.append(file)
                if len(batch) == batch_size:
                    batch_number += 1
                    log.info(f"Processing batch number {batch_number}")
                    try:
                        with ThreadPoolExecutor() as executor:
                            results = executor.map(lambda file: process_file(s3, s3_bucket, file['Key']), batch)
                            text_list.extend(filter(None, results))
                    except Exception as e:
                        log.error(f"Error processing batch number {batch_number}: {e}")
                    batch = []

        # Process any remaining files in the last batch
        if batch:
            batch_number += 1
            log.info(f"Processing batch number {batch_number}")
            try:
                with ThreadPoolExecutor() as executor:
                    results = executor.map(lambda file: process_file(s3, s3_bucket, file['Key']), batch)
                    text_list.extend(filter(None, results))
            except Exception as e:
                log.error(f"Error processing batch number {batch_number}: {e}")

    except KeyboardInterrupt:
        log.info("Process interrupted by user")
        return text_list
    except Exception as e:
        log.error(f"Error retrieving documents from S3: {e}")

    log.info("Completed retrieving documents from S3 in batches")
    return text_list

def data_splitter(documents):
    log.info("Calling data_splitter")
    log.info("Starting to split documents")

    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
        split_texts = []
        for doc in documents:
            chunk = text_splitter.split_text(doc)
            split_texts.extend(chunk)
        log.info("Completed split documents")
        return split_texts
    except Exception as e:
        log.error(f"Error splitting documents: {e}")
        return []

def create_faiss_index(documents, index_id):
    log.info(f"Calling create_faiss_index for index {index_id}")
    try:
        vectorstore_faiss = FAISS.from_documents(documents, bedrock_embeddings)
        directory = f'/tmp/faiss_index_{index_id}'
        if not os.path.exists(directory):
            os.makedirs(directory)
        vectorstore_faiss.save_local(directory)
        return directory
    except Exception as e:
        log.error(f"Error creating FAISS index {index_id}: {e}")
        return None

def save_faiss_to_s3(directory):
    print("Starting to rename and upload files from /tmp directories")
    try:
        s3 = boto3.client('s3')
        base_dir = '/tmp'
        
        for directory in os.listdir(base_dir):
            dir_path = os.path.join(base_dir, directory)
            if os.path.isdir(dir_path) and directory.startswith('faiss_index_'):
                index_id = directory.split('_')[-1].strip()
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    file_extension = file.split('.')[-1]
                    new_file_name = f"index_{index_id}.{file_extension}"
                    s3_key = f'{s3_faiss}{new_file_name}'
                    print(f"Uploading {file_path} to S3 at {s3_key}")
                    with open(file_path, 'rb') as f:
                        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=f.read())
        print("Completed renaming and uploading files from /tmp directories")
    except Exception as e:
        print(f"Error renaming and uploading files: {e}")


def process_batch(batch, index_id):
    log.info(f"Calling process_batch for batch {index_id}")
    try:
        documents = [Document(page_content=text) for text in batch]
        directory = create_faiss_index(documents, index_id)
        if directory:
            save_faiss_to_s3(directory)
    except Exception as e:
        log.error(f"Error processing batch {index_id}: {e}")

def generate_multiple_faiss_indices(documents, batch_size=100):
    log.info("Calling generate_multiple_faiss_indices")
    batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
    with ThreadPoolExecutor() as executor:
        for index_id, batch in enumerate(batches):
            log.info(f"Submitting batch {index_id + 1} for processing")
            executor.submit(process_batch, batch, index_id + 1)

def generate_vectors():
    log.info("Calling generate_vectors")
    log.info("Starting to generate Vectors")
    try:
        list_text = get_documents_from_s3_in_batches(bucket_name, prefix)
        splitted_text = data_splitter(list_text)
        generate_multiple_faiss_indices(splitted_text)
        log.info("Finished Generating Vectors")
    except Exception as e:
        log.error(f"Error generating vectors: {e}")

if __name__ == "__main__":
    generate_vectors()