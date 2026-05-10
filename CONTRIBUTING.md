# Contributing to ACAS Pro

Thank you for your interest in contributing to ACAS Pro! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- Docker (optional, for full stack testing)

### Setup Steps

```bash
# 1. Clone the repository
git clone https://github.com/acas-pro/acas-pro.git
cd acas-pro

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# 3. Install dependencies
make install-dev

# 4. Run tests
make test

# 5. Start development server
make run
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style (run `make format`)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linting
make lint

# Run security scan
make security
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "type: description"
```

Commit message format:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add tests`
- `refactor: code restructuring`
- `chore: maintenance tasks`

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

Example:
```python
def process_user_data(user_id: str, data: dict) -> dict:
    """Process user data and return result.
    
    Args:
        user_id: Unique user identifier
        data: User data dictionary
        
    Returns:
        Processed data dictionary
    """
    result = {"user_id": user_id, "processed": True}
    return result
```

### Testing

- Write unit tests for all new functions
- Aim for >80% code coverage
- Use pytest fixtures for common setup
- Mock external services (LLM APIs, databases)

Example:
```python
def test_password_validation():
    """Test password validation rules."""
    result = password_validator.validate("weak")
    assert not result.is_valid
    assert "8 characters" in result.errors[0]
```

### Documentation

- Add docstrings to public functions
- Update README.md if adding features
- Update API documentation (OpenAPI spec)
- Add ADR for architectural decisions

## Pull Request Process

1. **Before Submitting**
   - All tests pass
   - Code is formatted with black
   - No linting errors
   - Security scan passes

2. **PR Description**
   - Describe what changed and why
   - Reference any related issues
   - Include testing notes

3. **Review Process**
   - Maintainers will review within 2 business days
   - Address review comments
   - Keep PRs focused and reasonably sized

4. **After Merge**
   - Delete your branch
   - Update related documentation

## Reporting Issues

### Bug Reports

Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version)
- Error messages/logs

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternatives considered

## Security

- Never commit secrets or API keys
- Report security issues privately
- Follow security best practices
- Run `make security` before submitting

## Questions?

- Check existing documentation
- Search closed issues
- Ask in discussions

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

Thank you for contributing!
