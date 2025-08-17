FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    TERRAFORM_VERSION=1.8.4

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
      git \
      curl \
      gnupg \
      apt-transport-https \
      lsb-release \
      ca-certificates \
      unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip -o terraform.zip \
 && unzip terraform.zip \
 && mv terraform /usr/local/bin/terraform \
 && chmod +x /usr/local/bin/terraform \
 && rm terraform.zip

# Install Node.js and ESLint
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get update && apt-get install -y nodejs \
 && npm install -g eslint \
 && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" \
     | tee /etc/apt/sources.list.d/google-cloud-sdk.list \
 && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
     | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
 && apt-get update \
 && apt-get install -y google-cloud-cli \
 && rm -rf /var/lib/apt/lists/*

# Optional: disable update prompts
RUN gcloud config set disable_usage_reporting true \
 && gcloud config set component_manager/disable_update_check true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY .env .

ARG GITHUBAPP_USER_NAME
ARG GITHUBAPP_USER_EMAIL
ENV GITHUBAPP_USER_NAME=$GITHUBAPP_USER_NAME \
    GITHUBAPP_USER_EMAIL=$GITHUBAPP_USER_EMAIL
RUN git config --global user.name "$GITHUBAPP_USER_NAME" \
 && git config --global user.email "$GITHUBAPP_USER_EMAIL"

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
