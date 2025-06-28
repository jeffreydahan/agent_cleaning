# Use an official Python runtime as a parent image.
# Using python:3.11-slim to keep the image size small.
FROM python:3.11-slim

# Install ffmpeg, which is required for video stream capture.
# --no-install-recommends reduces image size.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container.
WORKDIR /app

# Copy the dependencies file to the working directory.
COPY requirements.txt .

# Install any needed packages specified in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container.
COPY main.py .

# Command to run the application using Gunicorn, a production-ready WSGI server.
# Cloud Run automatically sets the PORT environment variable.
# We set a long timeout to accommodate potentially long video recording times.
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app