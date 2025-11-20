# Contributing to ZedNet

Thank you for your interest in contributing to ZedNet!

## Code of Conduct

Be respectful, inclusive, and professional.

## How to Contribute

### Reporting Bugs

1. Check if bug already reported
2. Include:
   - ZedNet version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs (redact sensitive info)

### Suggesting Features

1. Check existing feature requests
2. Explain use case clearly
3. Consider security implications

### Code Contributions

#### Setup

```bash
git clone https://github.com/cns-studios/zednet.git
cd zednet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

#### Development Workflow

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/your-feature`
3. **Make changes**
4. **Test**: `pytest tests/ -v`
5. **Format**: `black core/ server/ gui/`
6. **Lint**: `flake8 core/ server/ gui/`
7. **Commit**: Use clear, descriptive messages
8. **Push**: `git push origin feature/your-feature`
9. **Pull Request**: Describe changes, link issues

#### Code Standards

- **Security first**: All code must pass security review
- **Test coverage**: Minimum 80% for new code
- **Documentation**: Docstrings for all public functions
- **Type hints**: Use Python type hints
- **PEP 8**: Follow Python style guide

#### Testing

```bash
# All tests
pytest tests/ -v --cov

# Security tests (must pass 100%)
pytest tests/test_security.py -v

# Specific test
pytest tests/test_security.py::TestPathSanitization -v
```

## Priority Areas

- **Security auditing** (critical)
- **BEP 46 implementation**
- **GUI improvements**
- **Documentation**
- **Cross-platform testing**

## Questions?

- **GitHub Discussions**: For general questions
- **GitHub Issues**: For bugs/features