from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tarxemo-django-clickpesa",
    version="0.1.0",
    author="TarXemo",
    description="A Django library for integrating ClickPesa mobile money and payout services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tarxemo/tarxemo-django-clickpesa",
    packages=find_packages(exclude=["tests*", "bhumwi*"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 5.0",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Django>=3.2",
        "requests>=2.25.0",
    ],
)
