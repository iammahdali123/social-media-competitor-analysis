from setuptools import setup, find_packages

setup(
    name="social-media-etl",
    version="1.0.0",
    description=(
        "Distributed ETL pipeline that transforms raw social media data from six "
        "Pakistani fashion giants into a high-performance Star Schema with automated "
        "'Campaign Type' and 'Comment Intent' classification for real-time competitive "
        "intelligence."
    ),
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "sqlalchemy>=2.0.0",
        "faker>=19.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ]
    },
)
