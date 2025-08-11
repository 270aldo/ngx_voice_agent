# Contributing to NGX Voice Sales Agent

Thank you for your interest in contributing to NGX Voice Sales Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct (see CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/270aldo/agent.SDK/issues)
2. If not, create a new issue using the bug report template
3. Include as much detail as possible

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue using the feature request template
3. Explain the use case and benefits

### Contributing Code

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/270aldo/agent.SDK.git
cd agent.SDK

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow existing patterns and conventions
   - Add tests for new functionality

3. **Run tests locally**
   ```bash
   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=html

   # Run specific test file
   pytest tests/unit/test_specific.py
   ```

4. **Check code quality**
   ```bash
   # Run linting
   ruff check src/ tests/

   # Run type checking
   mypy src/

   # Run security scan
   bandit -r src/
   ```

5. **Commit your changes**
   ```bash
   # Pre-commit hooks will run automatically
   git add .
   git commit
   # Follow the commit message prompts
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

### Commit Message Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

Example:
```
feat(ml): add adaptive learning for objection handling

Implemented ML-based objection prediction and response optimization
using historical conversation data and outcome tracking.

Closes #123
```

### Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass
   - Update documentation if needed
   - Add tests for new functionality
   - Verify no security issues

2. **PR Requirements:**
   - Fill out the PR template completely
   - Link related issues
   - Ensure CI checks pass
   - Request reviews from maintainers

3. **Review Process:**
   - Address reviewer feedback
   - Keep PR scope focused
   - Maintain clean commit history

### Code Style Guidelines

#### Python
- Follow PEP 8
- Use Black for formatting (configured in pre-commit)
- Maximum line length: 88 characters
- Use type hints for all functions

```python
def calculate_score(
    user_input: str,
    context: Dict[str, Any],
    threshold: float = 0.8
) -> float:
    """Calculate relevance score for user input.
    
    Args:
        user_input: The user's message
        context: Current conversation context
        threshold: Minimum score threshold
        
    Returns:
        Relevance score between 0 and 1
    """
    # Implementation
    pass
```

#### Documentation
- Write clear docstrings for all public functions
- Keep README and other docs up to date
- Include examples where helpful

### Testing Guidelines

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

```python
def test_calculate_score_with_valid_input():
    # Arrange
    user_input = "I need help with pricing"
    context = {"topic": "sales"}
    
    # Act
    score = calculate_score(user_input, context)
    
    # Assert
    assert 0 <= score <= 1
    assert score > 0.5  # Should be relevant
```

### Getting Help

- Join our discussions in [GitHub Discussions](https://github.com/270aldo/agent.SDK/discussions)
- Check the [documentation](docs/)
- Ask questions in issues with the "question" label

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Our contributors page

Thank you for contributing to NGX Voice Sales Agent! 🚀