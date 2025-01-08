name: Build and Deploy
ENV AWS_ACCESS_KEY_ID=your_access_key_id
ENV AWS_SECRET_ACCESS_KEY=your_secret_access_key
ENV AWS_DEFAULT_REGION=your_aws_region

on:
  push:
    branches:
      - main
  workflow_dispatch:
    inputs:
      deploy:
        description: 'Do you want to deploy the code?'
        required: true
        default: 'no'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v1

    - name: Login to Docker Hub
      uses: docker/login-action@v1
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v2
      with:
        context: .
        push: true
        tags: user/repo:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up SSH
      uses: webfactory/ssh-agent@v0.5.3
      with:
        ssh-private-key: ${{ secrets.EC2_SSH_KEY }}

    - name: Deploy to EC2
      if: ${{ github.event.inputs.deploy == 'yes' }}
      run: |
        ssh -o StrictHostKeyChecking=no ec2-user@3.145.41.180 << 'EOF'
          cd /LeaseManager
          git pull origin main
          npm install
          pm2 restart all
        EOF