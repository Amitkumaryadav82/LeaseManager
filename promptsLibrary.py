
template0 = """
This system is strictly built to provide information about the leases.
Given the user query below, classify it as either `Need SQL`, `Non SQL`, or `Other`.

- **Need SQL**: If the user query requires data to be fetched from the database tables, classify it as `Need SQL`. Only classify as "Need SQL" if data is available in the table mentioned below. Note that the table contains only quantitative data and not qualitative.
- **Non SQL**: If the user query does not require any data to be fetched from the database but needs information on the type of data present inside the lease documents, classify it as `Non SQL`.
- **Other**: If the user query is out of context, classify it as `Other`.

**Important Notes:**
- Do not respond in more than 2 words.
- Do not generate any additional prompts.
- If users ask you to check the details in the documents, classify it as "Non SQL".

**Table Details:**

CREATE TABLE leasemanagerdb.lease_details (
    document_id INT AUTO_INCREMENT PRIMARY KEY,
    lease_name VARCHAR(100),
    lease_date DATE,
    lessee_name VARCHAR(255),
    lessor_name VARCHAR(255),
    prop_address_line1 VARCHAR(255),
    prop_address_line2 VARCHAR(255),
    prop_city VARCHAR(100),
    prop_state VARCHAR(50),
    prop_zip_code VARCHAR(20),
    lease_start_date DATE,
    lease_end_date DATE,
    lease_duration INT,
    lease_duration_firm INT,
    prop_size DECIMAL(10, 2),
    monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2),
    lessee_signed BOOLEAN,
    lessor_signed BOOLEAN,
    no_parking_spaces INT,
    rent_1 DECIMAL(10, 2),
    rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2)
);

**Request:** {request}

**Classification:**
"""

### Create Chain for SQL Query Generation
# Build prompt
template1 = """
You are a MySQL expert. Given an input request, return a syntactically correct MySQL query to run.

- Query for All Results: Unless the user specifies a specific number of examples to obtain, query for all the results. Order the results to return the most informative data in the database.
- Selective Columns: Never query for all columns from a table. Query only the columns needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.
- Column Names: Use only the column names you can see in the tables below. Do not query for columns that do not exist. Pay attention to which column is in which table.
- Current Date: Use date('now') function to get the current date if the question involves "today".
- No New Columns or Aggregations: Do not return any new columns nor perform aggregation on columns. Return only the columns present in tables; further aggregations will be done by Python code in later steps.
- Python Code: Python code should be well formatted and must not have any indentation or syntactical errors.
- Database Connection Info: Information required to connect to the database like host, user, password, and database name are mentioned in settings.txt file.
- Query Format: The query should be generated in a single line.

Use the following format:

Request: Request here
SQLQuery: Generated SQL Query here

Only use the following tables:
CREATE TABLE IF NOT EXISTS leasemanagerdb.lease_details (
    document_id INT AUTO_INCREMENT PRIMARY KEY,
    lease_name VARCHAR(100),
    lease_date DATE,
    lessee_name VARCHAR(255),
    lessor_name VARCHAR(255),
    prop_address_line1 VARCHAR(255),
    prop_address_line2 VARCHAR(255),
    prop_city VARCHAR(100),
    prop_state VARCHAR(50),
    prop_zip_code VARCHAR(20),
    lease_start_date DATE,
    lease_end_date DATE,
    lease_duration INT,
    lease_duration_firm INT,
    prop_size DECIMAL(10, 2),
    monthly_rent DECIMAL(10, 2),
    monthly_rent_firm DECIMAL(10, 2),
    lessee_signed BOOLEAN,
    lessor_signed BOOLEAN,
    no_parking_spaces INT,
    rent_1 DECIMAL(10, 2),
    rent_2 DECIMAL(10, 2),
    rent_3 DECIMAL(10, 2)
);

Please note that lease_name contains the unique lease id.

Request: {request}
SQLQuery: 
"""
template4 = """
Use the given context and the request to answer the question.
If you don't know the answer, say you don't know.
Keep the answer concise and ensure that it is not more than 250 words.
Ensure that the answer is grammatically correct and does not contain any incomplete sentences.
Do not copy text directly from the lease document. Instead, provide a proper summary and then cite the references based on which the summary is generated.
Be specific in your response. Do not provide any additional details unless required.

Context: {context}
Request: {request}
Answer:
"""
