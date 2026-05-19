# Use official lightweight Python image
FROM local-only/base-python-cpu:latest

LABEL IMAGE="extension-api"
LABEL BUILD_IGNORE="False"

# Set working directory
WORKDIR /app

# Install python requirements
COPY files/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY files/app/ ./

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run the FastAPI server
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

RUN chmod +x /app/boot.sh

CMD ["/app/boot.sh"]