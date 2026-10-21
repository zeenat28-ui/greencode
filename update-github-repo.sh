#!/bin/bash
# GitHub Repository Update Script for Hackathon
# Run this with: bash update-github-repo.sh

echo "🚀 Updating GitHub repository metadata for Amazon Hackathon..."

# Update repository description and homepage
gh repo edit zeenat28-ui/greencode \
  --description "Voice-operated Software Carbon Intelligence Engine powered by Amazon Alexa+, Amazon Bedrock AI, and AWS. Measures real hardware energy, calculates ISO/IEC 21031 SCI scores, and auto-fixes energy waste with verified AI refactoring." \
  --homepage "https://greencode-teal.vercel.app"

echo "✅ Description and homepage updated"

# Add topics/tags (judges filter by these!)
gh repo edit zeenat28-ui/greencode \
  --add-topic amazon-alexa \
  --add-topic amazon-bedrock \
  --add-topic aws \
  --add-topic sustainability \
  --add-topic green-software \
  --add-topic carbon-emissions \
  --add-topic energy-efficiency \
  --add-topic finops \
  --add-topic developer-tools \
  --add-topic voice-assistant \
  --add-topic mcp \
  --add-topic model-context-protocol \
  --add-topic alexa-skills \
  --add-topic hackathon \
  --add-topic iso-21031 \
  --add-topic typescript \
  --add-topic python \
  --add-topic react

echo "✅ Topics added"
echo ""
echo "🎉 Done! Check your repo:"
echo "   https://github.com/zeenat28-ui/greencode"
