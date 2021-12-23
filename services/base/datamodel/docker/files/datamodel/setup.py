import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kaapana-datamodel", # Replace with your own username
    version="0.0.1",
    author="Kaapana Team",
    #author_email="author@example.com",
    description="Toolbox to interact with data stored by kaapana.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.kaapana.ai/",
    project_urls={
        "Bug Tracker": "https://phabricator.mitk.org",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(where="."),
    python_requires=">=3.6",
    install_requires=[
        'PyYAML',
    ]
)