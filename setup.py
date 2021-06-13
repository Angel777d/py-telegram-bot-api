import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="py-telegram-bot-api",
    version="0.0.8",
    description="Simple, one file, zero dependency Telegram bot api wrapper",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/Angel777d/py-telegram-bot-api",
    author="Angelovich",
    author_email="angel777da@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["telegram_bot_api", ],
    include_package_data=True,
    install_requires=[],
)
