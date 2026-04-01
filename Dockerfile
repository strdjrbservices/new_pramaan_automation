# Use the official Microsoft Playwright image as base
# This image contains all necessary system dependencies for Chromium
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 5000

# Set working directory
WORKDIR /app

# Install project dependencies and git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the app knows it is in production
ENV RENDER=true

# Create necessary directories
RUN mkdir -p Downloads/Full\ File Downloads/Revised Downloads/Old Downloads/HTMLFiles Downloads/logfiles

# Expose the internal port Render will use
EXPOSE 5000

# Start the application using gunicorn for production stability
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "app:app"]
