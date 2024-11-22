FROM python:3.10.6-buster

# Copy the entire project directory
COPY . /app

# Set the working directory
WORKDIR /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install the project in editable mode
RUN pip install -e .

# Command to run the application
CMD ["uvicorn", "API.scraper:app", "--host", "0.0.0.0", "--port", "8080"]

