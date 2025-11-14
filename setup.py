#!/usr/bin/env python3
"""
Setup configuration for Muratura FEM package
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

# Version
VERSION = '7.0.0-alpha'

setup(
    name='muratura-fem',
    version=VERSION,
    description='Sistema di calcolo strutturale FEM per murature secondo NTC 2018',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='Muratura FEM Contributors',
    author_email='',
    url='https://github.com/mikibart/Muratura',
    project_urls={
        'Bug Reports': 'https://github.com/mikibart/Muratura/issues',
        'Source': 'https://github.com/mikibart/Muratura',
    },
    license='MIT',
    packages=find_packages(exclude=['tests', 'examples', 'docs']),
    include_package_data=True,
    package_data={
        'Material': [
            'data/*.yaml',
            'data/*.json',
            'reports/templates/*.tex',
        ],
    },
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.24.0,<2.0.0',
        'scipy>=1.10.0,<2.0.0',
        'matplotlib>=3.7.0,<4.0.0',
        'pandas>=2.0.0,<3.0.0',
        'typing-extensions>=4.5.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.4.0',
            'pylint>=2.17.0',
        ],
        'docs': [
            'sphinx>=6.0.0',
            'sphinx-rtd-theme>=1.2.0',
        ],
        'bim': [
            'ifcopenshell>=0.7.0',  # BIM/IFC import-export (Phase 3)
        ],
        'reports': [
            'jinja2>=3.1.0',         # LaTeX template engine (Phase 3)
            'python-docx>=1.1.0',    # Word document generation (Phase 3)
            'openpyxl>=3.1.0',       # Excel export (optional)
        ],
        'all': [
            # Development
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.4.0',
            'pylint>=2.17.0',
            # Documentation
            'sphinx>=6.0.0',
            'sphinx-rtd-theme>=1.2.0',
            # BIM Integration
            'ifcopenshell>=0.7.0',
            # Reports
            'jinja2>=3.1.0',
            'python-docx>=1.1.0',
            'openpyxl>=3.1.0',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    keywords='fem structural-engineering masonry ntc2018 eurocode8 pushover seismic '
             'bim ifc revit archicad historic-buildings heyman frp frcm strengthening '
             'floors balconies stairs vaults arches knowledge-levels',
    entry_points={
        'console_scripts': [
            # Nessun CLI per ora, ma si può aggiungere
            # 'muratura-cli=Material.cli:main',
        ],
    },
)
