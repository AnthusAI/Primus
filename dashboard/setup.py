from setuptools import setup, find_packages

setup(
    name="primus-dashboard",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "python-dotenv",
        "gql[requests]>=3.0.0",
        "boto3",
        "requests_aws4auth",
    ],
    entry_points={
        "console_scripts": [
            "primus-dashboard=primus_dashboard.cli:cli",
        ],
    },
) 