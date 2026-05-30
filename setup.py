from setuptools import find_packages, setup


setup(
    name="ai-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "rich",
        "typer",
    ],
    entry_points={
        "console_scripts": [
            "ai-cli=ai_cli.main:app",
        ],
    },
)
