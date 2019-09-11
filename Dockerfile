# Extend the base Python image
# See https://hub.docker.com/_/python for version options
# N.b., there are many options for Python images. We used the plain
# version number in the pilot. YMMV. See this post for a discussion of
# some options and their pros and cons:
# https://pythonspeed.com/articles/base-image-python-docker-images/
FROM python:3.7

# Give ourselves some credit
LABEL maintainer "DataMade <info@datamade.us>"

# Install and upgrade pip
# This may not be necessary, depending on your base Python image
RUN apt-get update && \
    apt-get install -y binutils libproj-dev gdal-bin

# Inside the container, create an app directory and switch into it
RUN mkdir /app
WORKDIR /app

# Copy the requirements file into the app directory, and install them. Copy
# only the requirements file, so Docker can cache this build step. Otherwise,
# the requirements must be reinstalled every time you build the image after
# the app code changes. See this post for further discussion of strategies
# for building lean and efficient containers:
# https://blog.realkinetic.com/building-minimal-docker-containers-for-python-applications-37d0272c52f3
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the contents of the current host directory (i.e., our app code) into
# the container.
COPY . /app
