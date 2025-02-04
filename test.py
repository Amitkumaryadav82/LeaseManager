# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set AWS environment variables
ENV AWS_ACCESS_KEY_ID=your_access_key_id
ENV AWS_SECRET_ACCESS_KEY=your_secret_access_key
ENV AWS_DEFAULT_REGION=your_aws_region


# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV NAME World

CMD ["uvicorn", "getleaseAPI:app", "--host", "0.0.0.0", "--port", "8000"]