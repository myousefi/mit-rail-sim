from setuptools import find_packages, setup

setup(
    name="string_charts",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "stch=string_charts.stch:main",
        ],
    },
)
