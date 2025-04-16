from setuptools import setup

setup(
    name="TestForge",
    version="0.1.0",
    packages=["testforge"],
    install_requires=[
        "click",  # add all your dependencies here
    ],
    entry_points={
        "console_scripts": [
            "testforge = testforge.cli:main",  # link to your main function in cli.py
        ],
    },
)

