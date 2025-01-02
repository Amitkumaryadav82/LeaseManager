# import os
# import pandas as pd
# import pytesseract
# from PIL import Image
# from deepeval import evaluate
# from deepeval.dataset import EvaluationDataset
# from deepeval.test_case import LLMTestCase
# from deepeval.metrics import  AnswerRelevancyMetric
# from langchain_anthropic import ChatAnthropic
# from langchain_aws import BedrockEmbeddings
# import boto3
# import dash
# from dash import dcc

# import dash_html_components as html
# import tempfile
# import logging
# from utils import get_anthropic_llm, getSettings
# from CustomLLMEval import getCustomLLM

# # Initialize logging
# logging.basicConfig(level=logging.INFO)

# # Initialize S3 client
# s3 = boto3.client('s3')
# settings = getSettings()

# # Function to extract text from images using OCR
# def extract_text_from_image(image_path):
#     try:
#         image = Image.open(image_path)
#         text = pytesseract.image_to_string(image)
#         return text
#     except Exception as e:
#         logging.error(f"Error extracting text from image {image_path}: {e}")
#         return ""

# # Function to prepare the dataset from images stored in S3 bucket
# def prepare_dataset_from_s3(bucket_name, file_keys):
#     data = {'query': ["for the lease agreement with M.A.S. REAL ESTATE SERVICES LTD., what is the notice period for termination of lease",
#                     "What is the  approved Tenant Improvement Budget for the lease with High Range SV1 LLC for the property in Scottsdale, Arizona",
#                     "For Lease GS-09B-02614, where do I need to submit the invoices?"

#                         ],
#              'response': ["as per lease GS-09B-02625,lease can be terminated in partial or whole anytime after 10th year from the day of commencement by providing 90 days notices to Lessor",
#                         " As per lease GS-09B-02614, the Tentant improvement Budget is $1,311,799.00",
#                         "As per lease GS-09B-002614, invoices should be shall be submitted at: GSA  Office Of Finance, P.O. Box 17181, Fort Worth, TX-760102-0181"
#              ]}
    
#     with tempfile.TemporaryDirectory() as temp_dir:
#         for file_key in file_keys:
#             try:
#                 # Download the file from S3 to a temporary directory
#                 s3.download_file(bucket_name, file_key, os.path.join(temp_dir, os.path.basename(file_key)))
#                 image_path = os.path.join(temp_dir, os.path.basename(file_key))
                
#                 # Extract text from the image
#                 text = extract_text_from_image(image_path)
                
#                 # Append the query (file name) and response (extracted text) to the dataset
#                 data['query'].append(file_key)
#                 data['response'].append(text)
#             except Exception as e:
#                 logging.error(f"Error processing file {file_key}: {e}")
    
#     df = pd.DataFrame(data)
#     return df

# # Function to create test cases from the dataset
# def create_test_cases(df):
#     test_cases = []
#     for index, row in df.iterrows():
#         test_case = LLMTestCase(
#             input=row['query'],
#             actual_output=row['response'],
#             expected_output=row['response']  # Assuming the extracted text is the expected output
#         )
#         test_cases.append(test_case)
#     print("******** TEst cases created successfully")
#     return test_cases

# # Function to run the evaluation
# def run_evaluation(test_cases):
#     print("*** initializing Test cases")
#     print("Eval DAta set Initatized")
#     # metrics = [
#     #     ContextualPrecisionMetric(),
#     #     ContextualRecallMetric(),
#     #     ContextualRelevancyMetric()
#     # ]
    
#     evaluator_llm = get_anthropic_llm()
#     # evaluator_llm=getCustomLLM()
#     bedrock = boto3.client(service_name="bedrock-runtime")
#     evaluator_embeddings = BedrockEmbeddings(model_id=settings.get('embedding_model'),
#      client=bedrock)

#     print("***Settings done")
#     eval_dataset = EvaluationDataset(test_cases=test_cases)
#     print("******dataset done")
#     metric = AnswerRelevancyMetric(model="claude-3-opus-20240229")
#     print("Metric set")
#     result1= metric.measure(...)
#     print("Result1: ", result1)

#     results = evaluate(dataset=eval_dataset, metrics=metrics)
    
#     results_df = results.to_pandas()
#     return results_df

# # Function to create a dashboard using Dash
# def create_dashboard(results_df):
#     app = dash.Dash(__name__)
    
#     app.layout = html.Div([
#         html.H1('Evaluation Metrics Dashboard'),
#         dcc.Graph(
#             id='metrics-graph',
#             figure={
#                 'data': [
#                     {'x': results_df['Metric'], 'y': results_df['Score'], 'type': 'bar', 'name': 'Metrics'}
#                 ],
#                 'layout': {
#                     'title': 'Evaluation Metrics'
#                 }
#             }
#         )
#     ])
    
#     app.run_server(debug=True)

# # Main function to execute the evaluation and create the dashboard
# def getEvalMetrics():
#     bucket_name = 'capleasemanager'
#     file_keys = [
#         'lease/gsa_LAZ02625-Lease-1_Z-01.png', 'lease/gsa_LAZ02625-Lease-1_Z-02.png',
#         'gsa_LAZ02614-SLA-2-_Z-01.png','gsa_LAZ02614-SLA-2-_Z-02'
#     ]
    
#     df = prepare_dataset_from_s3(bucket_name, file_keys)
#     df.to_csv('lease_documents.csv', index=False)
    
#     test_cases = create_test_cases(df)
#     results_df = run_evaluation(test_cases)
#     print("************* ",results_df.head())
    
#     create_dashboard(results_df)
from getLeaseInfo import getLeaseInfo
# import evaluate
from rouge import Rouge
from sacrebleu.metrics import BLEU
from nltk.translate.bleu_score import sentence_bleu
import numpy as np


def getEvalMetrics():
    rouge_scorer = Rouge()

    query = [
        "for the lease agreement with M.A.S. REAL ESTATE SERVICES LTD., what is the notice period for termination of lease",
        "What is the approved Tenant Improvement Budget for the lease with High Range SV1 LLC for the property in Scottsdale, Arizona",
        "For Lease GS-09B-02614, where do I need to submit the invoices?"
    ]

    response = [
        "As per lease GS-09B-02625, lease can be terminated in partial or whole anytime after 10th year from the day of commencement by providing 90 days notice to Lessor",
        "As per lease GS-09B-02614, the Tenant Improvement Budget is $1,311,799.00",
        "As per lease GS-09B-002614, invoices should be submitted at: GSA Office Of Finance, P.O. Box 17181, Fort Worth, TX-760102-0181"
    ]

    total_rouge_score = 0
    total_bleu_score = 0

    for i in range(3):
        rouge_score = rouge_scorer.get_scores(query[i], response[i])
        total_rouge_score += rouge_score[0]["rouge-l"]["f"]
        bleu_score = sentence_bleu([response[i].split()], query[i].split())
        total_bleu_score += bleu_score

    avg_rouge = total_rouge_score / 3
    avg_bleu = total_bleu_score / 3

    print("** Rouge: ", avg_rouge)
    print("** BLEU: ", avg_bleu)

    return avg_bleu, avg_rouge

if __name__ == '__main__':
    avg_bleu, avg_rouge = getEvalMetrics()
    print("**Avg BLEU: ", avg_bleu)
    print("**Avg ROUGE: ", avg_rouge)