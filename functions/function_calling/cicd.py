"""CI/CD Automation — generate pipeline configs for GitHub Actions, Docker, AWS.

Agents can call these tools to auto-generate deployment pipelines, cutting
setup time dramatically.
"""

import json
import os
import textwrap
from typing import Any, Dict, List


def generate_github_actions(
    project_name: str,
    language: str,
    test_command: str = "",
    deploy_target: str = "none",
    branch: str = "main",
) -> str:
    """
    Generate a complete GitHub Actions CI/CD workflow YAML for a project.

    Args:
        project_name (str): Name of the project (used in workflow title).
        language (str): Primary language: python, node, go, rust, java, ruby, php.
        test_command (str): The command to run tests, e.g. "pytest" or "npm test".
        deploy_target (str): Deployment target: none, vercel, netlify, aws-eb, heroku, docker-hub.
        branch (str): Branch that triggers the workflow. Defaults to "main".

    Returns:
        str: JSON with keys: filename (suggested path) and content (YAML text).
    """
    lang = language.lower()

    # Language-specific setup steps
    setup_steps = {
        "python": textwrap.dedent(f"""
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt || true"""),
        "node": textwrap.dedent(f"""
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci"""),
        "go": textwrap.dedent(f"""
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'"""),
        "rust": textwrap.dedent(f"""
      - uses: actions-rust-lang/setup-rust-toolchain@v1"""),
        "java": textwrap.dedent(f"""
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'"""),
    }.get(lang, "")

    test_step = ""
    if test_command:
        test_step = f"""
      - name: Run tests
        run: {test_command}"""

    deploy_steps = {
        "vercel": """
      - name: Deploy to Vercel
        run: npx vercel --prod --token ${{ secrets.VERCEL_TOKEN }}""",
        "netlify": """
      - name: Deploy to Netlify
        run: npx netlify-cli deploy --prod --auth ${{ secrets.NETLIFY_TOKEN }} --site ${{ secrets.NETLIFY_SITE_ID }}""",
        "docker-hub": """
      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/{project_name}:latest""".format(project_name=project_name.lower().replace(" ", "-")),
        "aws-eb": """
      - name: Deploy to AWS Elastic Beanstalk
        uses: einaregilsson/beanstalk-deploy@v21
        with:
          aws_access_key: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws_secret_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          application_name: {project_name}
          environment_name: {project_name}-prod
          region: us-east-1
          version_label: ${{ github.sha }}""".format(project_name=project_name),
        "heroku": """
      - name: Deploy to Heroku
        uses: akhileshns/heroku-deploy@v3.13.15
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: {project_name}
          heroku_email: ${{ secrets.HEROKU_EMAIL }}""".format(project_name=project_name.lower().replace(" ", "-")),
    }.get(deploy_target, "")

    yaml_content = f"""name: {project_name} CI/CD

on:
  push:
    branches: [ {branch} ]
  pull_request:
    branches: [ {branch} ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{setup_steps}{test_step}

  deploy:
    needs: build-and-test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/{branch}' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
{setup_steps}{deploy_steps}
"""
    return json.dumps({
        "filename": ".github/workflows/ci-cd.yml",
        "content": yaml_content,
        "language": lang,
        "deploy_target": deploy_target,
    }, indent=2)


def generate_dockerfile(language: str, app_port: int = 8000, entry_point: str = "") -> str:
    """
    Generate an optimized Dockerfile for a project.

    Args:
        language (str): Project language: python, node, go, rust, java.
        app_port (int): The port your application listens on. Defaults to 8000.
        entry_point (str): Main entry command, e.g. "python app.py" or "npm start".

    Returns:
        str: JSON with keys: filename and content (Dockerfile text).
    """
    lang = language.lower()
    dockerfiles = {
        "python": f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {app_port}
CMD {json.dumps((entry_point or "python app.py").split())}
""",
        "node": f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE {app_port}
CMD {json.dumps((entry_point or "node server.js").split())}
""",
        "go": f"""FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE {app_port}
CMD ["./main"]
""",
        "rust": f"""FROM rust:1.77 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /usr/local/bin/app
EXPOSE {app_port}
CMD ["app"]
""",
        "java": f"""FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY . .
RUN ./mvnw package -DskipTests || gradle build

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE {app_port}
ENTRYPOINT ["java", "-jar", "app.jar"]
""",
    }
    content = dockerfiles.get(lang, dockerfiles["python"])
    return json.dumps({"filename": "Dockerfile", "content": content, "language": lang}, indent=2)


def generate_docker_compose(services: str, with_database: str = "none") -> str:
    """
    Generate a docker-compose.yml for a multi-service application.

    Args:
        services (str): Comma-separated service names and their types, e.g.
                        "api:python,frontend:node,worker:python".
        with_database (str): Add a database service: none, postgres, mysql, mongodb, redis.

    Returns:
        str: JSON with keys: filename and content (docker-compose YAML text).
    """
    parsed_services = []
    for svc in services.split(","):
        svc = svc.strip()
        if ":" in svc:
            name, lang = svc.split(":", 1)
        else:
            name, lang = svc, "python"
        parsed_services.append((name.strip(), lang.strip()))

    service_blocks = []
    for name, lang in parsed_services:
        port = 8000 if lang == "python" else 3000
        service_blocks.append(f"""  {name}:
    build: ./{name}
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
    depends_on: []
    restart: unless-stopped""")

    db_blocks = {
        "postgres": """  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped""",
        "mysql": """  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: app
    volumes:
      - mysqldata:/var/lib/mysql
    restart: unless-stopped""",
        "mongodb": """  mongodb:
    image: mongo:7
    volumes:
      - mongodata:/data/db
    ports:
      - "27017:27017"
    restart: unless-stopped""",
        "redis": """  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped""",
    }.get(with_database, "")

    volumes_block = {
        "postgres": "\nvolumes:\n  pgdata:",
        "mysql": "\nvolumes:\n  mysqldata:",
        "mongodb": "\nvolumes:\n  mongodata:",
    }.get(with_database, "")

    all_services = "\n".join(service_blocks)
    if db_blocks:
        all_services += "\n" + db_blocks

    content = f"""version: '3.9'

services:
{all_services}
{volumes_block}
"""
    return json.dumps({"filename": "docker-compose.yml", "content": content}, indent=2)


def generate_aws_codepipeline(project_name: str, repo_owner: str, repo_name: str,
                               deploy_stack: str = "ecs") -> str:
    """
    Generate an AWS CodePipeline CloudFormation template for CI/CD.

    Args:
        project_name (str): Name of the project/pipeline.
        repo_owner (str): GitHub owner/org for the source repo.
        repo_name (str): GitHub repository name.
        deploy_stack (str): Deployment target: ecs, lambda, s3, eb (Elastic Beanstalk).

    Returns:
        str: JSON with keys: filename and content (CloudFormation YAML template).
    """
    content = f"""AWSTemplateFormatVersion: '2010-09-09'
Description: CodePipeline for {project_name}

Parameters:
  GitHubToken:
    Type: String
    NoEcho: true
    Description: GitHub personal access token

Resources:
  ArtifactBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "{project_name.lower()}-artifacts-${{AWS::AccountId}}"

  CodeBuildRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: codebuild.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AdministratorAccess

  CodeBuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: {project_name}-build
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/standard:7.0
        Type: LINUX_CONTAINER
        PrivilegedMode: true
      Source:
        Type: CODEPIPELINE
        BuildSpec: buildspec.yml

  PipelineRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: codepipeline.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AdministratorAccess

  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: {project_name}-pipeline
      RoleArn: !GetAtt PipelineRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
      Stages:
        - Name: Source
          Actions:
            - Name: GitHub_Source
              ActionTypeId:
                Category: Source
                Owner: ThirdParty
                Provider: GitHub
                Version: '1'
              Configuration:
                Owner: {repo_owner}
                Repo: {repo_name}
                Branch: main
                OAuthToken: !Ref GitHubToken
              OutputArtifacts:
                - Name: source
        - Name: Build
          Actions:
            - Name: CodeBuild
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              InputArtifacts:
                - Name: source
              Configuration:
                ProjectName: !Ref CodeBuildProject
              OutputArtifacts:
                - Name: built
"""
    return json.dumps({
        "filename": f"cloudformation/{project_name}-pipeline.yml",
        "content": content,
        "deploy_stack": deploy_stack,
    }, indent=2)
