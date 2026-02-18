# Contributing to TradingView Webhook Bot

First off, thank you for considering contributing to this project! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

## 🤝 How Can I Contribute?

### 1. Reporting Bugs
Bugs are tracked as GitHub issues. When filing an issue, explain the problem and include additional details to help maintainers reproduce the problem:
*   Use a clear and descriptive title.
*   Describe the exact steps which reproduce the problem.
*   Provide specific examples to demonstrate the steps.
*   Describe the behavior you observed after following the steps.

### 2. Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues.
*   Use a clear and descriptive title.
*   Provide a step-by-step description of the suggested enhancement.
*   Explain why this enhancement would be useful.

### 3. Pull Requests
The process described here has several goals:
*   Maintain the quality of the product.
*   Fix problems that are important to users.
*   Engage the community in working toward the best possible product.

**Steps to Contribute:**

1.  **Fork the repo** and create your branch from `main`.
2.  **Environment Setup**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
3.  **Make your changes**.
4.  **Test your changes**:
    Ensure all existing tests pass and add new tests if applicable.
    ```bash
    python -m unittest discover tests
    ```
5.  **Commit your changes** using descriptive commit messages (e.g., `feat: add new signal validator`).
6.  **Push** to your fork and submit a **Pull Request**.

## 💻 Coding Standards

*   **Language**: Python 3.10+
*   **Style**: We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/).
*   **Formatting**: Please format your code using `black` before committing.
*   **Type Hinting**: Use Python type hints for all function arguments and return values.

## 📁 Project Structure

*   `app/core`: Configuration and Singletons (DB, Logging).
*   `app/services`: Business logic. Avoid putting API logic here.
*   `app/api`: FastAPI routers and request models.
*   `app/models`: SQLAlchemy database models.

Thank you for your contributions! 🚀
