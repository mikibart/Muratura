"""
Setup configuration for MasonryFEMEngine package
"""

from setuptools import setup, find_packages
import pathlib

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text(encoding='utf-8')

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    requirements = []
    with open(HERE / filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                # Skip version constraints for development tools
                if not any(skip in line.lower() for skip in ['sphinx', 'black', 'flake8', 'mypy']):
                    requirements.append(line)
    return requirements

setup(
    name="muratura",
    version="1.0.0",
    description="Sistema completo di analisi strutturale per murature secondo NTC 2018",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/mikibart/Muratura",
    author="MasonryFEM Contributors",
    author_email="",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="structural-engineering masonry fem ntc2018 seismic-analysis",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "viz": [
            "matplotlib>=3.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            # Add CLI tools if needed in future
            # "muratura-cli=muratura.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/mikibart/Muratura/issues",
        "Source": "https://github.com/mikibart/Muratura",
        "Documentation": "https://muratura.readthedocs.io/",
    },
)
