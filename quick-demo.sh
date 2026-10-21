#!/bin/bash
# GreenCode Quick Demo Setup

echo "🚀 GreenCode Auditor - Quick Demo Setup"
echo "========================================"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install from https://docker.com"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found"; exit 1; }

echo "✓ Prerequisites check passed"
echo ""

# Start services
echo "Starting services..."
docker-compose -f docker-compose.demo.yml up -d

echo ""
echo "✅ GreenCode is starting!"
echo ""
echo "📱 Open in browser:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000/docs"
echo ""
echo "🎯 Quick Demo Steps:"
echo "   1. Click 'Demo Login' button"
echo "   2. Paste sample code or enter GitHub URL"
echo "   3. Click 'Run Scan'"
echo "   4. Review energy anti-patterns"
echo "   5. Click 'Generate Fix' to see AI refactoring"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.demo.yml logs -f"
echo ""
echo "🛑 Stop demo:"
echo "   docker-compose -f docker-compose.demo.yml down"
