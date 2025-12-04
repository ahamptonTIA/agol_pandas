from pathlib import Path
from setuptools import setup, find_packages

here = Path(__file__).parent

# readme if present
readme = (here / "README.md").read_text(encoding="utf8") if (here / "README.md").exists() else ""

setup(
    name="agol_pandas",
    version="0.1.0",
    description="Utilities for working between ArcGIS Online hosted tables and pandas DataFrames",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/ahamptonTIA/agol_pandas",
    author="ahamptonTIA",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "pandas>=1.0",
        "arcgis",  # ArcGIS Python API
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
