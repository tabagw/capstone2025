#!/bin/bash

# Configuration
FUNCTION_NAME="cooking-captain-function"
REGION="us-east-1"

echo "🔨 Building deployment package..."

# Create deployment directory
rm -rf deployment
mkdir -p deployment

# Install dependencies
pip install -r requirements.txt -t deployment/

# Copy source files
cp src/*.py deployment/

# Create ZIP file
cd deployment
zip -r ../lambda-deployment.zip .
cd ..

echo "📦 Deployment package created: lambda-deployment.zip"

# Upload to Lambda
echo "⬆️  Uploading to AWS Lambda..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://lambda-deployment.zip \
    --region $REGION

echo "✅ Deployment complete!"

# Clean up
rm -rf deployment
rm lambda-deployment.zip