import os
import pandas as pd
import pytesseract
from PIL import Image
from deepeval import evaluate
from deepeval.dataset import EvaluationDataset
from deepeval.test_case import LLMTestCase
from deepeval.metrics import ContextualPrecisionMetric, ContextualRecallMetric, ContextualRelevancyMetric
from langchain_anthropic import ChatAnthropic
from langchain_aws import BedrockEmbeddings
import boto3
import dash
from dash import dcc

import dash_html_components as html
import tempfile
import logging
from utils import get_anthropic_llm, getSettings

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')
settings = getSettings()

# Function to extract text from images using OCR
def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image {image_path}: {e}")
        return ""

# Function to prepare the dataset from images stored in S3 bucket
def prepare_dataset_from_s3(bucket_name, file_keys):
    data = {'query': [], 'response': []}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for file_key in file_keys:
            try:
                # Download the file from S3 to a temporary directory
                s3.download_file(bucket_name, file_key, os.path.join(temp_dir, os.path.basename(file_key)))
                image_path = os.path.join(temp_dir, os.path.basename(file_key))
                
                # Extract text from the image
                text = extract_text_from_image(image_path)
                
                # Append the query (file name) and response (extracted text) to the dataset
                data['query'].append(file_key)
                data['response'].append(text)
            except Exception as e:
                logging.error(f"Error processing file {file_key}: {e}")
    
    df = pd.DataFrame(data)
    return df

# Function to create test cases from the dataset
def create_test_cases(df):
    test_cases = []
    for index, row in df.iterrows():
        test_case = LLMTestCase(
            input=row['query'],
            actual_output=row['response'],
            expected_output=row['response']  # Assuming the extracted text is the expected output
        )
        test_cases.append(test_case)
    return test_cases

# Function to run the evaluation
def run_evaluation(test_cases):
    eval_dataset = EvaluationDataset(test_cases=test_cases)
    
    metrics = [
        ContextualPrecisionMetric(),
        ContextualRecallMetric(),
        ContextualRelevancyMetric()
    ]
    
    evaluator_llm = get_anthropic_llm()
    bedrock = boto3.client(service_name="bedrock-runtime")
    evaluator_embeddings = BedrockEmbeddings(model_id=settings.get('embedding_model'), client=bedrock)

    results = evaluate(dataset=eval_dataset, metrics=metrics)
    
    results_df = results.to_pandas()
    return results_df

# Function to create a dashboard using Dash
def create_dashboard(results_df):
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1('Evaluation Metrics Dashboard'),
        dcc.Graph(
            id='metrics-graph',
            figure={
                'data': [
                    {'x': results_df['Metric'], 'y': results_df['Score'], 'type': 'bar', 'name': 'Metrics'}
                ],
                'layout': {
                    'title': 'Evaluation Metrics'
                }
            }
        )
    ])
    
    app.run_server(debug=True)

# Main function to execute the evaluation and create the dashboard
def getEvalMetrics():
    bucket_name = 'capleasemanager'
    file_keys = [
        'lease/gsa_(R)LDC02066-Lease-SF2-01.png', 'lease/gsa_(R)LDC02066-Lease-SF2-02.png',
        'lease/gsa_(R)LDC02066-Lease-SF2-03.png', 'lease/gsa_(R)LDC02066-Lease-SF2-04.png',
        'lease/gsa_(R)LDC02066-Lease-SF2-05.png'
    ]
    
    df = prepare_dataset_from_s3(bucket_name, file_keys)
    df.to_csv('lease_documents.csv', index=False)
    
    test_cases = create_test_cases(df)
    results_df = run_evaluation(test_cases)
    print(results_df.head())
    
    create_dashboard(results_df)

if __name__ == '__main__':
    getEvalMetrics()
