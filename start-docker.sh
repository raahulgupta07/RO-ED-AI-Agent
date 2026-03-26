#!/bin/bash

echo "======================================================"
echo "       RO-ED-Lang Docker Installation Script           "
echo "======================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "Docker is running"
echo ""

# Check if .env file exists
if [ ! -f backend/.env ]; then
    echo "Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo ""
    echo "IMPORTANT: Edit backend/.env and add your OPENROUTER_API_KEY"
    echo "   File location: backend/.env"
    echo ""
    echo "Press Enter after you've added your API key..."
    read
fi

# Check if API key is set
if grep -q "sk-or-v1-your-openrouter-key-here" backend/.env 2>/dev/null; then
    echo "ERROR: OpenRouter API key not set in backend/.env"
    echo "Please edit backend/.env and add your actual API key"
    exit 1
fi

echo "API key configured"
echo ""

# Build and start containers
echo "Building Docker containers..."
echo "This may take 3-5 minutes on first run..."
echo ""

docker-compose down 2>/dev/null
docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================"
    echo "            Installation Complete!                      "
    echo "======================================================"
    echo ""
    echo "Access the application:"
    echo "   Streamlit UI: http://localhost:8080"
    echo ""
    echo "Check status:"
    echo "   docker-compose ps"
    echo ""
    echo "View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "Stop containers:"
    echo "   docker-compose down"
    echo ""
else
    echo ""
    echo "ERROR: Docker build failed"
    echo "Check the error messages above"
    echo "Try: docker-compose logs"
    exit 1
fi
