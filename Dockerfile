# Use the Miniconda base image
FROM continuumio/miniconda3:latest

# Set the working directory in the container
WORKDIR /app

# Optionally, copy your environment.yml if you use one
# COPY environment.yml /app/environment.yml

# Create a new conda environment and install packages
# Using an environment.yml file:
# RUN conda env create -f /app/environment.yml

# Or directly with conda create
RUN conda create --name appenv -c conda-forge python=3.12.2 keplergl -y && \
    conda clean --all -y

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "appenv", "/bin/bash", "-c"]

# Your previous Dockerfile commands for copying files and setting CMD can remain the same
# Copy the dependencies file to the working directory if you use pip in addition to Conda
COPY requirements.txt .

# Install any additional needed packages specified in requirements.txt with pip
# Note: It's best to use Conda packages when available to avoid compatibility issues
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard]

# Copy the content of the local src directory to the working directory
COPY . .

# Specify the command to run on container start
CMD ["/opt/conda/envs/appenv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# Expose the port the app runs on
EXPOSE 8000
