FROM python:3.10.7

# Set the working directory
WORKDIR /

# Copy everything into the working directory
COPY . .

# Run updates, install python3-pip, install required packages
RUN apt-get -y update
RUN apt-get update && apt-get install -y python python3-pip
RUN pip3 install -r requirements.txt

ENV HOST=0.0.0.0
ENV PORT=8000

# Expose the following port for the container
EXPOSE $PORT

# Run the gunicorn wsgi server, bind the following address
CMD gunicorn wsgi:app