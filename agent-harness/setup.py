from setuptools import find_namespace_packages, setup


setup(
    name="cli-anything-ones",
    version="0.1.0",
    description="Agent-friendly read-only CLI for ONES issues and attachments.",
    python_requires=">=3.10",
    packages=find_namespace_packages(
        include=["cli_anything.*"],
        exclude=["cli_anything.ones.tests", "cli_anything.ones.tests.*"],
    ),
    include_package_data=True,
    package_data={
        "cli_anything.ones": ["skills/*.md"],
    },
    install_requires=["click>=8.0"],
    entry_points={
        "console_scripts": [
            "cli-anything-ones=cli_anything.ones.ones_cli:main",
        ],
    },
)
