# Contributing to Squash PDF Compressor

Thank you for considering contributing to Squash! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Squash.git
   cd Squash
   ```

3. **Set up development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

4. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use Black for formatting: `black src/`
- Use Flake8 for linting: `flake8 src/`
- Add type hints for function parameters and returns
- Write docstrings for all public functions and classes

### Testing

- Write unit tests for new features
- Ensure tests pass: `pytest`
- Maintain test coverage ≥70%: `pytest --cov=squash`
- Test on Windows 10/11 before submitting

### Commit Messages

Use clear, descriptive commit messages:
- `feat: Add drag-and-drop support`
- `fix: Correct file size calculation`
- `docs: Update README with installation steps`
- `test: Add tests for batch processing`

### Pull Request Process

1. **Update tests** - Add tests for new features
2. **Update documentation** - Update README, docstrings, etc.
3. **Run tests** - Ensure all tests pass
4. **Format code** - Run Black and Flake8
5. **Create PR** - Submit pull request with clear description

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] All tests passing
- [ ] Tested on Windows 10/11

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

## Areas for Contribution

### High Priority
- Drag-and-drop functionality (tkinterdnd2 integration)
- Settings dialog implementation
- History tracking feature
- Custom preset editor

### Medium Priority
- CLI interface improvements
- Additional quality presets
- Performance optimizations
- UI/UX enhancements

### Documentation
- User guide improvements
- API documentation
- Tutorial videos
- FAQ updates

## Reporting Bugs

Use GitHub Issues with the bug template:

**Title**: Brief description of bug

**Description**:
- What happened?
- What did you expect?
- Steps to reproduce
- Screenshots (if applicable)

**Environment**:
- Windows version
- Squash version
- Python version (if running from source)

## Feature Requests

Use GitHub Issues with the feature template:

**Title**: Brief feature description

**Description**:
- Use case and motivation
- Proposed solution
- Alternative solutions considered
- Additional context

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect differing viewpoints
- Accept responsibility for mistakes

### Enforcement

Unacceptable behavior may result in:
- Warning
- Temporary ban
- Permanent ban

Report issues to: [email/contact]

## Questions?

- 📖 Check [Documentation](docs/)
- 💬 Open a [Discussion](https://github.com/ACWul/Squash/discussions)
- 🐛 Report [Issues](https://github.com/ACWul/Squash/issues)

Thank you for contributing to Squash! 🎉
