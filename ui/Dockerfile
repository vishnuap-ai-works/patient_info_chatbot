# Use a base image that includes Python
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install Streamlit and dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app code into the container
COPY streamlit_app.py /app/

# Expose the Streamlit port (8501)
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "streamlit_app.py"]