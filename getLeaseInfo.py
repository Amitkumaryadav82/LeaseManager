import json
import os
import boto3
import tempfile
import traceback
import numpy as np
# from sklearn.metrics import precision_score, recall_score

## LLm Models
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.llms import Bedrock
from langchain_aws import BedrockEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from langchain_community.vectorstores import FAISS
# from langchain_core.evaluation import BLEU, ROUGE

from promptsLibrary import template0, template1, template4
from utils import getSettings, runQuery, get_anthropic_llm
from logger import getLogger

settings = getSettings()
log = getLogger()

s3_key = "faiss/"
s3_bucket = "capleasemanager"

## Bedrock Clients
bedrock = boto3.client(service_name="bedrock-runtime")
bedrock_embeddings = BedrockEmbeddings(model_id=settings.get('embedding_model'), client=bedrock)

# S3 client
s3 = boto3.client("s3")
log = getLogger()

def read_faiss_s3(s3_key, bucket_name):
    log.info("************ inside read_faiss_s3")
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_key)
    files = response.get('Contents', [])
    
    log.info("Files found in S3 bucket:")
    for file in files:
        log.info(file['Key'])
    
    faiss_files = [file['Key'] for file in files if file['Key'].endswith('.faiss')]
    pkl_files = [file['Key'] for file in files if file['Key'].endswith('.pkl')]
    
    if not faiss_files or not pkl_files:
        raise FileNotFoundError("FAISS index files not found in the specified S3 bucket and prefix.")
    
    log.info(f"Number of FAISS files found: {len(faiss_files)}")
    log.info(f"Number of PKL files found: {len(pkl_files)}")
    
    vectorstore_faiss = None
    merged_count = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for faiss_file, pkl_file in zip(faiss_files, pkl_files):
            faiss_file_path = os.path.join(temp_dir, os.path.basename(faiss_file))
            pkl_file_path = os.path.join(temp_dir, os.path.basename(pkl_file))
            s3.download_file(bucket_name, faiss_file, faiss_file_path)
            s3.download_file(bucket_name, pkl_file, pkl_file_path)
            
            if not os.path.exists(faiss_file_path) or not os.path.exists(pkl_file_path):
                raise FileNotFoundError(f"FAISS files not found at {faiss_file_path} and {pkl_file_path}")
            
            log.info(f"Loading FAISS index from {faiss_file_path} and {pkl_file_path}")
            try:
                current_vectorstore_faiss = FAISS.load_local(temp_dir, bedrock_embeddings, allow_dangerous_deserialization=True, index_name=os.path.splitext(os.path.basename(faiss_file))[0])
                if vectorstore_faiss is None:
                    vectorstore_faiss = current_vectorstore_faiss
                    log.info(f"Initial FAISS index loaded from {faiss_file_path}")
                else:
                    log.info(f"Merging FAISS index from {faiss_file_path}")
                    vectorstore_faiss.merge_from(current_vectorstore_faiss)
                    merged_count += 1
            except Exception as e:
                log.error(f"Error merging FAISS index from {faiss_file_path}: {e}")
    
    total_files_processed = merged_count + 1  # Including the initial assignment
    log.info(f"Total FAISS files processed: {total_files_processed}")
    return vectorstore_faiss    

vectorstore_faiss = read_faiss_s3("faiss/", "capleasemanager")

def initializePromptAndChains(request, history):
    try:
        llm = get_anthropic_llm()
        PROMPT0 = PromptTemplate(input_variables=["request", "history"], template=template0)
        clf_chain = (PROMPT0
                     | llm
                     | StrOutputParser())
        log.info(f"received clfchain ")
        
        PROMPT1 = PromptTemplate(input_variables=["request", "history"], template=template1)
        log.info(f"Set Prompt1")
        sql_chain = (PROMPT1
                     | llm
                     | StrOutputParser())
        log.info(f"Set SQL ChainSet ")

        PROMPT4 = ChatPromptTemplate.from_messages(
            [
                ("system", template4),
                ("human", "{input}"),
            ]
        )
        log.info(f"set prompt4")
        retriever = vectorstore_faiss.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        log.info(f"rag chain initalized1")
        question_answer_rag_chain = create_stuff_documents_chain(llm, PROMPT4)
        log.info(f"rag chain initalized2")

        rag_chain = create_retrieval_chain(retriever, question_answer_rag_chain)
        log.info(f"rag chain initalized")
                
        sql_code_chain = sql_chain
        log.info(f"initialized chains")
        return clf_chain, sql_code_chain, rag_chain
    except Exception as e:
        log.error(f"Exception while initalizing chains: {e}")
        traceback.print_exc()

def extract_sql_query(response):
    parts = response.split('SQLQuery:')
    if len(parts) > 1:
        sql_query = parts[1].strip()
        return sql_query
    else:
        return None

def invoke_chain(request, clf_label, clf_chain, sql_code_chain, rag_chain, history):
    if "need sql" in clf_label.lower():
        log.info("inside need sql")
        code_response = sql_code_chain.invoke({"request": request, "history": history})
        log.info(f"code_response:", code_response)
        sql_query = extract_sql_query(code_response)
        log.info(f"SQL Query is ", sql_query)
        query_output = runQuery(sql_query)
        log.info(f"SQL Query output is ", query_output)
        extracted_values = [item[0] for item in query_output]
        output = json.dumps({"answer": extracted_values}, indent=4)
        log.info("json_output: ", output)

    elif "non sql" in clf_label.lower():
        log.info(f"inside non sql")
        raw_output = rag_chain.invoke({"input": request, "history": history})
        log.info(f"raw output: {raw_output['answer']} " )
        answer = raw_output["answer"]
        answer_json = {"answer": answer}
        output = json.dumps(answer_json, indent=4)
        log.info(output)
        
        # Evaluate generation
        reference_texts = [...]  # Add your reference texts here
        # avg_bleu, avg_rouge = evaluate_generation([answer], reference_texts)
        # log.info(f"Average BLEU Score: {avg_bleu}")
        # log.info(f"Average ROUGE Score: {avg_rouge}")
        
    else:
        log.info("inside need sql")
        output_quote = "The request is out of context."
        answer_json = {"answer": output_quote}
        output = json.dumps(answer_json, indent=4)
        log.info(f"output is: {output}")
    return output

def getLeaseInfo(request, history):
    try:
        log.info(f"the query is : {request}")
        clf_chain, sql_code_chain, rag_chain = initializePromptAndChains(request, history)
        clf_label = clf_chain.invoke({"request": request, "history": history})
        log.info(f"Received clf_label:  {clf_label}")
        output = invoke_chain(request, clf_label, clf_chain, sql_code_chain, rag_chain, history)
        output_json = {"response": output}
        final_output = json.dumps(output_json, indent=4)
        return final_output
    except Exception as e:
        log.error(f"Exception in getLease Info: {e}")
        traceback.print_exc()


# def evaluate_generation(generated_texts, reference_texts):
#     bleu = BLEU()
#     rouge = ROUGE()
    
#     bleu_scores = [bleu.compute(generated, reference) for generated, reference in zip(generated_texts, reference_texts)]
#     rouge_scores = [rouge.compute(generated, reference) for generated, reference in zip(generated_texts, reference_texts)]
    
#     avg_bleu = np.mean(bleu_scores)
#     avg_rouge = np.mean([score['rouge-l']['f'] for score in rouge_scores])
    
#     return avg_bleu, avg_rouge

if __name__ == "__main__":
    history = []
    while True:
        query = input("Please enter your query (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break

        history.append({"role": "user", "content": query})
        output_from_llm = getLeaseInfo(query, history)
        log.info("****** final output is: {output_from_llm}")
        print(output_from_llm)
        # Append the assistant's response to the history
        response_content = json.loads(output_from_llm)["response"]
        history.append({"role": "assistant", "content": response_content})