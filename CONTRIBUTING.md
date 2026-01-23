# Contributing to TraceLens

Thank you for your interest in contributing to TraceLens! This document provides guidelines and instructions for contributing to the project.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/certainly-param/tracelens.git
   cd tracelens
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/tracelens.git
   ```

## 🔧 Development Setup

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Environment Configuration

Create a `.env` file in the project root with your API keys:

```env
GOOGLE_API_KEY=your_api_key_here
# or
GEMINI_API_KEY=your_api_key_here
```

## 📝 Making Changes

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. **Make your changes** following our coding standards:
   - Follow existing code style and conventions
   - Add comments for complex logic
   - Update documentation as needed
   - Write or update tests if applicable

3. **Test your changes**:
   - Run the backend: `cd backend && uvicorn src.api.main:app --reload`
   - Run the frontend: `cd frontend && npm run dev`
   - Test the sample agent: `python backend/scripts/verify_telemetry.py`

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: description of your changes"
   ```
   
   Use clear, descriptive commit messages:
   - `Add:` for new features
   - `Fix:` for bug fixes
   - `Update:` for updates to existing features
   - `Refactor:` for code refactoring
   - `Docs:` for documentation changes

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub:
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots if UI changes are involved

## 📋 Code Style Guidelines

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings for public functions and classes

### TypeScript/React

- Use functional components with hooks
- Follow React best practices
- Use TypeScript types consistently
- Keep components focused and reusable

### General

- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions and components small and focused
- Follow existing patterns in the codebase

## 🧪 Testing

- Test your changes thoroughly before submitting
- Ensure existing functionality still works
- Test edge cases and error conditions
- If adding new features, include test cases when possible

## 📚 Documentation

- Update README.md if you add new features or change setup instructions
- Add comments to complex code sections
- Update API documentation if endpoints change
- Include examples in your PR description

## 🐛 Reporting Bugs

If you find a bug, please create an issue with:

- **Clear title** describing the bug
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Environment details** (OS, Python version, Node version, etc.)
- **Screenshots or logs** if applicable

## 💡 Suggesting Features

We welcome feature suggestions! Please create an issue with:

- **Clear description** of the feature
- **Use case** or problem it solves
- **Proposed implementation** (if you have ideas)
- **Alternatives considered** (if any)

## 🔍 Code Review Process

1. All submissions require review
2. Maintainers will review your PR
3. Address any feedback or requested changes
4. Once approved, your PR will be merged

## 📜 License

By contributing to TraceLens, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make TraceLens better for everyone. We appreciate your time and effort!

---

**Questions?** Feel free to open an issue or start a discussion!
