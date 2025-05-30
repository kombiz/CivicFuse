# CivicFuse - Advocacy Contact Management System

A modern, FastAPI-based contact management system designed for advocacy organizations to manage contacts, track engagement, and organize outreach efforts.

## 🎯 Overview

CivicFuse is a comprehensive advocacy CMS that enables organizations to:
- Manage contacts (activists, influencers, reporters)
- Organize contacts into groups
- Track social media profiles
- Log shared content and engagement
- Prepare for future AI-driven analysis and automation

## ✨ Features

### V1 Core Features
- **Contact Management**: Full CRUD operations for contacts with detailed profiles
- **Group Organization**: Create and manage contact groups for targeted outreach
- **Social Media Integration**: Manual linking of social media profiles (Twitter, BlueSky, LinkedIn, etc.)
- **Content Tracking**: Log and track content shared with contacts/groups
- **Modern UI**: Bootstrap 5-based responsive interface
- **API-First Design**: RESTful API with automatic OpenAPI documentation

### Future Roadmap
- Automated social media data collection
- AI-powered content analysis via Ollama
- Engagement tracking and analytics
- Meltwater integration for media monitoring
- Advanced search and filtering capabilities

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Local SupaBase instance (PostgreSQL)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kombiz/CivicFuse.git
   cd CivicFuse
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your SupaBase credentials
   ```

3. **Start the application**
   ```bash
   # Development mode
   make dev

   # Or using Docker Compose directly
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Initialize the database**
   ```bash
   # Run database schema creation
   make db-setup
   ```

5. **Access the application**
   - Web UI: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Alternative API docs: http://localhost:8000/redoc

## 📁 Project Structure

```
CivicFuse/
├── app/                    # Main application code
│   ├── api/               # API routes and endpoints
│   ├── models/            # Pydantic data models
│   ├── repositories/      # Database interaction layer
│   ├── services/          # Business logic layer
│   ├── templates/         # Jinja2 HTML templates
│   └── static/           # CSS, JS, and static assets
├── scripts/               # Database setup scripts
├── tests/                 # Test suite
├── docker/               # Docker configuration files
└── archive/              # Archived documentation and planning
```

## 🛠️ Development

### Available Make Commands
```bash
make dev          # Start development environment
make test         # Run test suite
make db-setup     # Initialize database schema
make clean        # Clean up containers and volumes
make logs         # View application logs
```

### API Endpoints

The application provides a RESTful API with the following main endpoints:

- **Contacts**: `/api/v1/contacts`
- **Groups**: `/api/v1/groups`
- **Social Profiles**: `/api/v1/social_profiles`
- **Shared Content**: `/api/v1/shared_content`

Full API documentation is available at `/docs` when running the application.

## 🗄️ Database Schema

The application uses PostgreSQL with the following main tables:
- `contacts` - Contact information and details
- `groups` - Contact groupings for organization
- `contact_group_memberships` - Many-to-many relationship between contacts and groups
- `social_profiles` - Social media profile links for contacts
- `shared_content_log` - Tracking of content shared with contacts/groups

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Production
```bash
docker-compose up --build
```

## 📖 Documentation

- **Getting Started**: See `GETTING_STARTED.md` for detailed setup instructions
- **Database Info**: See `database-info.md` for database schema details
- **API Documentation**: Available at `/docs` endpoint when running
- **Archived Docs**: Additional documentation available in `archive/` directory

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **Repository**: [https://github.com/kombiz/CivicFuse](https://github.com/kombiz/CivicFuse)
- **Issues**: [https://github.com/kombiz/CivicFuse/issues](https://github.com/kombiz/CivicFuse/issues)
- **Documentation**: Available in repository and at `/docs` endpoint

## 📞 Support

For questions, issues, or contributions, please:
1. Check existing [GitHub Issues](https://github.com/kombiz/CivicFuse/issues)
2. Create a new issue if needed
3. Reach out via the repository discussions

---

**CivicFuse** - Empowering advocacy through intelligent contact management. 