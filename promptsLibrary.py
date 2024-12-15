
template0 = """
Given the user query below, classify it as either being about `Need SQL`, `Non SQL`, or `Other`.
If the user query requires some data to be fetched from the database tables then classify it as `Need SQL`.
If the user query does not requires any data to be fetched from the database but instead need information on what type of data is present inside the database tables then classify it as `Non SQL`.
If the user query looks out of the context then classify it as `Other`.

Some examples of questions which should result in 'Need SQL' are mentioned below:
    Question1- How many unique lease are there?
    Query1 - select unique(lease_name) from lease_details
    Question2- Give me all the leases which are completing in 2025.
    Query2- Select lease_name from lease_details where EXTRACT(YEAR FROM lease_end_date) = 2025;
    Question3- Give me all the leases which started in 2024 and ending in 2027.
    Query3- SELECT * FROM leases WHERE EXTRACT(YEAR FROM start_date) = 2024  AND EXTRACT(YEAR FROM end_date) = 2027;
    Question4-Give me the sum of rent of all the leases for the year 2025
    Query4-SELECT SUM(rent) AS total_rent_2025 FROM leases WHERE EXTRACT(YEAR FROM start_date) <= 2025 AND EXTRACT(YEAR FROM end_date) >= 2025;

The databse has following tables:
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY, lease_name VARCHAR(100),lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );

Please note that lease_name contains the unique lease id

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
Use the following pieces of user request and sql query to generate python code that should first load the required data from 'lease_details' database and 
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
CREATE TABLE IF NOT EXISTS lease_details (document_id INT AUTO_INCREMENT PRIMARY KEY, lease_name VARCHAR(100),lease_date DATE,lessee_name VARCHAR(255),lessor_name VARCHAR(255),
   prop_address_line1 VARCHAR(255), prop_address_line2 VARCHAR(255), prop_city VARCHAR(100), prop_state VARCHAR(50), prop_zip_code VARCHAR(20),
    lease_start_date DATE, lease_end_date DATE, lease_duration INT, lease_duration_firm INT,  prop_size DECIMAL(10, 2), monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2), lessee_signed BOOLEAN, lessor_signed BOOLEAN, no_parking_spaces INT, rent_1 DECIMAL(10, 2), rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2) );
Please note that lease_name contains the unique lease id
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