# Use an official Python runtime as a parent image
FROM python:3.9.7-slim

# Set the working directory in the container to /src
WORKDIR /src

# Add the current directory contents into the container at /src
ADD . /src

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install the latest version of ecCodes
RUN wget https://confluence.ecmwf.int/download/attachments/45757960/eccodes-2.23.0-Source.tar.gz?api=v2 \
    && tar xzf eccodes-2.23.0-Source.tar.gz?api=v2 \
    && cd eccodes-2.23.0-Source \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make \
    && make install

# Install cfgrib
RUN pip install cfgrib

# Run app.py when the container launches
CMD gunicorn --bind :$PORT src.app:app.server