# Use official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port (default for Shiny)
EXPOSE 8000

# Run the Shiny app
#CMD ["sh", "-c", "git clone https://github.com/youruser/yourrepo.git app && cd app && shiny run app.py --host 0.0.0.0 --port 8000"]
CMD ["shiny", "run", "web_magnus.py", "--host", "0.0.0.0", "--port", "8000"]
