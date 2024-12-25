
template0 = """
This system is strictly build to provide information about the leases.
Given the user query below, classify it as either being about `Need SQL`, `Non SQL`, or `Other`.
If the user query requires some data to be fetched from the database tables then classify it as `Need SQL`. You should classify the user query as "Need SQL" only if data is available in the table mentioned below.
Note that able contains only quantitative data and not qualitative. 
If the user query does not requires any data to be fetched from the database but instead need information on what type of data is present inside the documents which are related with leases then classify it as `Non SQL`.
If the user query looks out of the context then classify it as `Other`.
Do not respond in more than 2 words.
Do not generate any additional prompts

Table details are mentioned below:
CREATE TABLE lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY, lease_name VARCHAR(100),lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );


Request: {request}
Classification:
"""

### Create Chain for SQL Query Generation
# Build prompt
template1 = """
You are a MySQL expert. Given an input request, return a syntactically correct MySQL query to run.
Unless the user specifies in the question a specific number of examples to obtain, query for all the results. You can order the results to return the most informative data in the database.
Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use date('now') function to get the current date, if the question involves "today".
Do not return any new columns nor perform aggregation on columns. Return only the columns present in tables and further aggregations will be done by python code in later steps.
Python code should be well formatted and must not have any indentation or syntactical errors.
Information required to connect to the database like host, user, password and database name are mentioned in settings.txt file.

Use the following format:

Request: Request here
SQLQuery: Generated SQL Query here

Only use the following tables:
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY, lease_name VARCHAR(100),lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );
Please note that lease_name contains the unique lease id
Request: {request}
SQLQuery:
"""

### Create Chain for Insights Generation
# Build prompt
template2 = """
# update the table name
Use the following pieces of user request and sql query to generate python code that should first load the required data from 'lease_details' table which is available in leasemanagedb database 
and then show insights related to that data. If the generated insights contains a figure or plot then that should be saved inside the 'figures' directory.
Generate and return python code only, no additional text.
Python code should be well formatted and must not have any indentation or syntactical errors. 
Ensure all the brackets are closed properly in the python code.
Information required to connect to the database like host, user, password and database name are mentioned in settings.txt file.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

{request_plus_sqlquery}

Generate code:
"""


template4= """
    Use the given context and the request to answer the question.
    If you don't know the answer, say you don't know.
    Keep the answer concise and ensure that answer is not more than 250 words.
    Ensure that answer is grammatically correct and it must not contains any incomplete sentences.
    While providing response, do not copy the text from the lease document directly, instead provide a proper summary and then provide references based on which summary is generated.
    
    Request: {request}
    Context: {context}
    """
