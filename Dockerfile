# Use an official Python runtime as a parent image
FROM python:3.9.7-slim

# Set the working directory in the container to /src
WORKDIR /src

# Add the current directory contents into the container at /src
ADD . /src

# Update pip
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    cmake \
    libeccodes-dev \
    && rm -rf /var/lib/apt/lists/*

# Install cfgrib
RUN pip install cfgrib

# Run app.py when the container launches
CMD gunicorn --bind :$PORT src.app:app.server