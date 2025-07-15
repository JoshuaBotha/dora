# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="directory-explorer",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A FastAPI web application for exploring directory sizes with interactive pie charts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/directory-explorer",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn[standard]>=0.20.0",
        "pydantic>=1.10.0",
    ],
    entry_points={
        "console_scripts": [
            "directory-explorer=directory_explorer.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "directory_explorer": ["static/*"],
    },
)

# # requirements.txt
# fastapi>=0.95.0
# uvicorn[standard]>=0.20.0
# pydantic>=1.10.0
# 
# # requirements-dev.txt
# fastapi>=0.95.0
# uvicorn[standard]>=0.20.0
# pydantic>=1.10.0
# pytest>=7.0.0
# pytest-asyncio>=0.21.0
# httpx>=0.24.0
# black>=23.0.0
# flake8>=6.0.0
# mypy>=1.0.0
# 
