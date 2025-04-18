from setuptools import find_packages, setup

setup(
    name="testforge-cli-utils",  # Unique name for PyPI
    version="0.1.6",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click",  # add all your dependencies here
    ],
    entry_points={
        "console_scripts": [
            "testforge = testforge_cli_utils.cli:main",  # Adjust if different
        ],
    },
    author="Marie Infantraj",
    description="CLI utilities for test automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
)
