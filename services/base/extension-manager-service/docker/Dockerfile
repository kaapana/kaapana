# Use official lightweight Python image
FROM local-only/base-python-cpu:latest

LABEL IMAGE="extension-api"
LABEL BUILD_IGNORE="False"
LABEL BUILD_LIB_CONTEXT="True"
# This image requires the kaapana/lib directory as a named build context.
# The build script handles this automatically.
# To build manually:
#   docker build --build-context lib=<path-to-kaapana>/lib -t <tag> .

# Set working directory
WORKDIR /app

# Copy lib packages from the named build context (kaapana/lib/)
COPY --from=lib kaapana_containers /lib/kaapana_containers
COPY --from=lib kaapana_extensions /lib/kaapana_extensions

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