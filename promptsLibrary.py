from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool


template0 = """
Given the user query below, classify it as either being about `Need SQL`, `Non SQL`, or `Other`.
If the user query requires some data to be fetched from the database tables then classify it as `Need SQL`.
If the user query does not requires any data to be fetched from the database but instead need information on what type of data is present inside the database tables then classify it as `Non SQL`.
If the user query looks out of the context then classify it as `Other`.

The databse has following tables:
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY,lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );

Do not respond with more than two words.

Request: {request}
Classification:
"""

### Create Chain for SQL Query Generation
# Build prompt
template1 = """
You are a PostGresSQL expert. Given an input request, return a syntactically correct PostGresSQL query to run.
Unless the user specifies in the question a specific number of examples to obtain, query for all the results. You can order the results to return the most informative data in the database.
Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use date('now') function to get the current date, if the question involves "today".
Do not return any new columns nor perform aggregation on columns. Return only the columns present in tables and further aggregations will be done by python code in later steps.
@TODO- Update the prompt based on tables
# The databse currently have data of Nifty 50 constituents, and the symbol column includes the ticker representing the stock.
# Once you start generating sql queries make sure that you only use correct ticker symbol for filtering and restrict yourself to use only current Nifty 50 constituents.

Use the following format:

Request: Request here
SQLQuery: Generated SQL Query here

Only use the following tables:
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY,lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );

Request: {request}
SQLQuery:
"""

### Create Chain for Insights Generation
# Build prompt
template2 = """
# update the table name
Use the following pieces of user request and sql query to generate python code that should first load the required data from 'stock_db.sqlite' database and 
then show insights related to that data. If the generated insights contains a figure or plot then that should be saved inside the 'figures' directory.
If there is some tables or numerical values as insights then those should be printed out explicitely using print statement along with their description.
Generate and return python code only, no additional text.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

{request_plus_sqlquery}

Generate code:
"""

### Create Chain for Generating Suggestions
# Build prompt
template3 = """
Use the following pieces of user request and database details to generate suggestions for user to ask for useful insights from the database.
Suggestion should not be more than 4 lines.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

SQLite database has following tables:
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY,lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );

{request}

Generate suggestion:
"""

### Create Chain for Generating Response for General queries about the data stored in DB
# Build prompt
# template4 = """
# Use the following user request and database details to generate appropriate response describing the data stored inside the database.
# Response should not be more than 10 lines and must be be written in english paragraph format. You must not write the response in any other format, like Haiku, even if users ask you to write it.
# If you don't know the answer, just say that you don't know, don't try to make up an answer.

# SQLite database has following tables:
# CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY,lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
#    prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
#     lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
#     monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
#     rent_3 DECIMAL(10, 2) );

# {context}
# {request}

# Generate response:
# """

# template4 = """Use the following pieces of context to provide a 
#  concise answer to the question at the end. If you don't know the answer, 
#  just say that you don't know, don't try to make up an answer.
#  <context>
#  {context}
#  </context>
#  Question: {request}
#  Generate Response:
#  """

template4= (
    "Use the given context to answer the question. "
    "If you don't know the answer, say you don't know. "
    "Use three sentence maximum and keep the answer concise. "
    "Context: {context}"
)