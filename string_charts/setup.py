from distutils.core import setup

setup(
    name="string_charts",
    version="0.1.0",
    packages=["string_charts"],
    entry_points={
        "console_scripts": [
            "stch = string_charts.stch:main",
        ],
    },
)
