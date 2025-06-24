from setuptools import setup, find_packages

setup(
    name="lincon",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=10.0.0",
    ],
    author="Matheus Alves",
    author_email="matheusalves@example.com",
    description="Linux Containerized - Uma ferramenta para migração de containers",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/mathewalves/lincon",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
)
