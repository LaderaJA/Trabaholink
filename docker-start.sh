#!/bin/bash
# Quick start script for Trabaholink Docker setup

set -e

echo "🐳 Trabaholink Docker Quick Start"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo "📝 Creating .env.docker from example..."
    cp .env.docker.example .env.docker
    
    # Generate a random SECRET_KEY
    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || openssl rand -base64 50)
    
    # Update the SECRET_KEY in .env.docker
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env.docker
    else
        # Linux
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env.docker
    fi
    
    echo "✅ Created .env.docker with a random SECRET_KEY"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env.docker and update:"
    echo "   - DB_PASSWORD (use a strong password)"
    echo "   - DJANGO_SUPERUSER_* (uncomment and set admin credentials)"
    echo ""
    read -p "Press Enter to continue after editing .env.docker, or Ctrl+C to exit..."
fi

echo ""
echo "🔨 Building Docker images (this may take 5-10 minutes on first run)..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose --env-file .env.docker up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Trabaholink is starting up!"
echo ""
echo "🌐 Access the application at: http://localhost:8000"
echo "🔧 Admin panel at: http://localhost:8000/admin"
echo ""
echo "📋 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop services:    docker-compose down"
echo "   Restart:          docker-compose restart"
echo "   Create superuser: docker-compose exec web python manage.py createsuperuser"
echo ""
echo "📖 For more information, see README_DOCKER.md"
echo ""
echo "🎉 Setup complete! Monitoring logs (Ctrl+C to exit)..."
echo ""

# Follow logs
docker-compose logs -f
