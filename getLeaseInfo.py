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
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool


# Vector Embedding And Vector Store
from langchain_community.vectorstores import FAISS
from promptsLibrary import template0,template1,template2,template3,template4

## Bedrock Clients
bedrock = boto3.client(service_name="bedrock-runtime")
bedrock_embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock)

# S3 client
s3 = boto3.client("s3")
s3_key = "faiss/"
s3_bucket = "capleasemanager"


def get_mistral_llm():
    try:
        llm = Bedrock(model_id="mistral.mistral-7b-instruct-v0:2", 
                client=bedrock, model_kwargs={'max_tokens': 200})
        print("*****got mistral LLM")
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
        llm= get_mistral_llm()
        print("********received LLM")
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

        ### Python tool for code execution
        python_repl = PythonREPL()
        repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=python_repl.run,
        )
        repl_tool.run("1+1")

        PROMPT2 = PromptTemplate(input_variables=["request_plus_sqlquery"], template=template2)

        # Code Generation Chain
        code_chain = (PROMPT2
                    | llm
                    | StrOutputParser()       # to get output in a more usable format
                    )
        
        PROMPT3 = PromptTemplate(input_variables=["request"], template=template3)

        # Suggestion Generation Chain
        sug_chain = (PROMPT3
                    | llm
                    | StrOutputParser()       # to get output in a more usable format
                    )
        
        # PROMPT4 = PromptTemplate(input_variables=["context", "request"], template=template4)
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
        sql_code_chain = sql_chain | code_chain
        print("*************** initialized chains")
        return clf_chain,sql_code_chain,rag_chain
    except Exception as e:
        print(f"Exception while initalizing chains: {e}")

#  Return the responses in json only
def getLeaseInfo(request):
    try:
        
        clf_chain,sql_code_chain,rag_chain= initializePromptAndChains(request)
        clf_label=clf_chain.invoke(request)
        print(f" Received clf_label:  {clf_label}")
        if "need sql" in clf_label.lower():
            ## Generate code for insights
            code_response = sql_code_chain.invoke(request)
            # print(code_response)
            ## Execute code
            output = repl_tool.run(code_response)
            # print(output)
        elif "non sql" in clf_label.lower():
            print(f"Called rag_chain")
            # output =rag_chain.invoke(input={"query":request}, context=vectorstore_faiss)
            output=rag_chain.invoke({"input":request})
            # output=rag_chain.invoke({"input":{"context":vectorstore_faiss,"request": request}})
        else:
            output = "The request is out of context."
        print(f"********output is: {output}")
        return output
    except Exception as e:
        print(f"Exception in getLease Info: {e}")
        traceback.print_exc() 

if __name__== "__main__":
    query ="What is the lease number of the lease?"
    getLeaseInfo(query)




# def getLeaseInfo(query):
#     try:
#         # for filename in os.listdir('figures'):
#         # file_path = os.path.join('figures', filename)
#         # if os.path.isfile(file_path) and filename != '__init__.py':
#         #     os.remove(file_path)  # Remove file

#          # Route the user request to necessary chain
#         clf_label = clf_chain.invoke({"request":query})

#         if "need sql" in clf_label.lower():
#             ## Generate code for insights
#             code_response = sql_code_chain.invoke({"request": query})
#             # print(code_response)
#             ## Execute code
#             output = repl_tool.run(code_response)
#             # print(output)
#         elif "non sql" in clf_label.lower():
#             output = gnrl_chain.invoke({"request": query})
#         else:
#             output = "The request is out of context."

#         # Generate suggestions
#         # TODO: Do we need it?
#         # suggest = sug_chain.invoke({"request": query})
        
#         # If image is present inside 'figures' directory then Send the plot image to the chat
#         # if len(os.listdir('figures')) > 1:
#         #     for imgfile in os.listdir('figures'): 
#         #         print(imgfile)
#         #         if os.path.isfile(os.path.join('figures', imgfile)) and imgfile != '__init__.py':
#         #             # Attach the image to the message and send response, image, and suggestions
#         #             image = cl.Image(path="./figures/"+imgfile, name="image1", size="large", display="inline")
#         #             await cl.Message(
#         #                 content=f"Response: \n{output}", 
#         #                 elements=[image]
#         #                 ).send()
#         #             await cl.Message(content=f"Further suggestions: \n{suggest}",).send()
#         # else:
#         #     # Send response and suggestions
#         #     await cl.Message(content=f"Response: \n{output}",).send()
#         #     await cl.Message(content=f"Further suggestions: \n{suggest}",).send()
#         return output
#     except Exception as e:
#         raise HTTPException (status_code=500,detail=str(e))


# def getLeaseInfo(query):
#     try:
#         llm = get_mistral_llm()  # Create the LLaMA2 model instance
#         s3_key = "faiss/"
#         s3_bucket = "capleasemanager"
#         vectorstore_faiss = read_faiss_s3(s3_key, s3_bucket)
#         response = get_response_llm(llm, vectorstore_faiss, query)
#         print("Response:", response)
#         return response
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# prompt_template = """
# Human: Use the following pieces of context to provide a 
# concise answer to the question at the end. If you don't know the answer, 
# just say that you don't know, don't try to make up an answer.
# <context>
# {context}
# </context>
# Question: {question}
# Assistant:
# """

# PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

# def get_response_llm(llm, vectorstore_faiss, query):
#     qa = RetrievalQA.from_chain_type(
#         llm=llm,
#         chain_type="stuff",
#         retriever=vectorstore_faiss.as_retriever(search_type="similarity", search_kwargs={"k": 3}),
#         return_source_documents=True,
#         chain_type_kwargs={"prompt": PROMPT}
#     )
#     answer = qa({"query": query})
#     return answer['result']
