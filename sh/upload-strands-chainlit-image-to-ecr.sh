#!/usr/bin/env bash

# upload Docker Hub image to AWS ECR (only ECR allowed for custom runtime)

ECR_IMAGE="strands-chainlit:latest"
DOCKER_IMAGE="didierdurand/$ECR_IMAGE"

REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

echo "region: $REGION - account id: $ACCOUNT_ID - ECR uri: $ECR_URI"

docker pull "$DOCKER_IMAGE"
docker tag  "$DOCKER_IMAGE" "$ECR_URI/$ECR_IMAGE"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"

docker push "$ECR_URI/$ECR_IMAGE"




