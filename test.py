from getLeaseInfo import getLeaseInfo  # Replace 'your_module' with the actual module name

def test_continuous_queries():
    # Initialize an empty list to store responses
    responses = []
    session_id = "test_session"

    while True:
        # Get user input
        query = input("Please enter your query (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break

        # Get the response
        response = getLeaseInfo(query, session_id)
        responses.append(response)
        print(f"Query: {query}")
        print(f"Response: {response}")
        print("-" * 50)

    # Check if the responses are maintaining context
    assert len(responses) > 0, "There should be at least one response"

if __name__ == "__main__":
    test_continuous_queries()