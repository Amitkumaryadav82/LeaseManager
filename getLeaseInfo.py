import json
import os
import boto3
import tempfile
import traceback

## LLm Models
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate

# from langchain.chains import RetrievalQA
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.llms import Bedrock
from langchain_aws import BedrockEmbeddings
from langchain_anthropic import ChatAnthropic

from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool

# Vector Embedding And Vector Store
from langchain_community.vectorstores import FAISS
# from promptsLibrary import template0,template1,template2,template4
from promptsLibrary import template0,template1,template4

from utils import getSettings, runQuery

settings =getSettings()
# settings = {}
# with open('settings.txt', 'r') as file:
#     for line in file:
#         if line.strip():  # Ignore empty lines
#             key, value = line.strip().split('=')
#             settings[key] = value

# print(settings)

s3_key = "faiss/"
s3_bucket = "capleasemanager"


## Bedrock Clients
bedrock = boto3.client(service_name="bedrock-runtime")
bedrock_embeddings = BedrockEmbeddings(model_id=settings.get('embedding_model'), client=bedrock)

# S3 client
s3 = boto3.client("s3")

def initializeREPLTool():
    ### Python tool for code execution
        python_repl = PythonREPL()
        repl = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=python_repl.run,
        )
        repl.run("1+1")
        return repl

def get_anthropic_llm():
    try:
        llm=model = ChatAnthropic(model='claude-3-opus-20240229')
        print("**** Got Anthropic model")
        return llm
    except Exception as e:
        print("****Exception while getting anthropic: {e}")

def get_mistral_llm():
    try:
        llm = Bedrock(model_id= settings.get('mistral_model'), 
                client=bedrock, model_kwargs={'max_tokens': 200})
        print("*****got mistral LLM")
        return llm
    except Exception as e:
        print("Exception getting Mistral: {e}")

def get_llama_llm():
    try:
        llm = Bedrock(model_id= settings.get('llama_model'), 
                client=bedrock, model_kwargs={'max_gen_len': 512, 'top_p':0.1})
        print("*****got Llama LLM")
        return llm
    except Exception as e:
        print("Exception getting Mistral: {e}")


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
    print("********* received faiss")
    return vectorstore_faiss

vectorstore_faiss = read_faiss_s3("faiss/", "capleasemanager")


def initializePromptAndChains(request):
    try:
        # llm= get_mistral_llm()
        # llm=get_llama_llm()
        llm=get_anthropic_llm()
        print("********received anthropic model")
        PROMPT0 = PromptTemplate(input_variables=["request"], template=template0)
        print("********** received prompt0 ")
        # Classification Chain
        clf_chain = (PROMPT0
                    | llm
                    | StrOutputParser()       # to get output in a more usable format
                    )
        print(f"********** received clfchain ")
        
        PROMPT1 = PromptTemplate(input_variables=["request"], template=template1)
        print("********** received prompt1 ")
        # SQL Query Generation Chain
        sql_chain = (PROMPT1
                    | llm
                    | StrOutputParser()       # to get output in a more usable format
                    )

        # PROMPT2 = PromptTemplate(input_variables=["request_plus_sqlquery"], template=template2)

        # # Code Generation Chain
        # code_chain = (PROMPT2
        #             | llm
        #             | StrOutputParser()       # to get output in a more usable format
        #             )
        print("********** SQL ChainSet ")

        PROMPT4 =ChatPromptTemplate.from_messages(
            [
                ("system", template4),
                ("human","{input}"),
            ]
        )
        # General Response Chain with FAISS Retriever
        retriever = vectorstore_faiss.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        question_answer_rag_chain=create_stuff_documents_chain(llm,PROMPT4)
        rag_chain=create_retrieval_chain(retriever,question_answer_rag_chain)
                
        # Club SQL + Code generation chains
        # sql_code_chain = sql_chain | code_chain
        sql_code_chain = sql_chain
        print("*************** initialized chains")
        return clf_chain,sql_code_chain,rag_chain
    except Exception as e:
        print(f"Exception while initalizing chains: {e}")


def extract_sql_query(response):
    # Split the response by 'SQLQuery:'
    parts = response.split('SQLQuery:')
    if len(parts) > 1:
        # The SQL query is the part after 'SQLQuery:'
        sql_query = parts[1].strip()
        return sql_query
    else:
        return None

def invoke_chain(request,clf_label,clf_chain,sql_code_chain,rag_chain):
    if "need sql" in clf_label.lower():
        print("***** inside need sql")
        ## Generate code for insights
        code_response = sql_code_chain.invoke(request)
        print(f"*********code_response:", code_response)
        sql_query=extract_sql_query(code_response)
        print(f"****** SQL Query is ", sql_query)
        query_output=runQuery(sql_query)
        print(f"****** SQL Query output is ", query_output)
        # Extract values from the query output
        extracted_values = [item[0] for item in query_output]
        json_output = json.dumps({"extracted_values": extracted_values}, indent=4)
        print("***json_output: ",json_output)
        return json_output

    elif "non sql" in clf_label.lower():
        print(f" inside non sql...Called rag_chain")
        raw_output=rag_chain.invoke({"input": request})
        # Accessing the page_content attribute of the Document object
        page_content = raw_output["context"][0].page_content
        # Creating a dictionary with the page_content
        page_content_json = {"page_content": page_content }
        output = json.dumps(page_content_json, indent=4)
        print(output)
        
    else:
        print("***** inside need sql")
        output = "The request is out of context."
        print(f"********output is: {output}")
    return output

#  Return the responses in json only
def getLeaseInfo(request):
    try:
        print("**** the query is :", request)
        clf_chain,sql_code_chain,rag_chain= initializePromptAndChains(request)
        clf_label=clf_chain.invoke(request)
        print(f" Received clf_label:  {clf_label}")
        output=invoke_chain(request,clf_label, clf_chain,sql_code_chain,rag_chain)
        output_json = {"response": output }
        final_output = json.dumps(output_json, indent=4)
        return final_output
    except Exception as e:
        print(f"Exception in getLease Info: {e}")
        traceback.print_exc() 


if __name__== "__main__":
    query = input("Please enter your query: ")
    output_from_llm = getLeaseInfo(query)
    print("****** final output is: ", output_from_llm)

