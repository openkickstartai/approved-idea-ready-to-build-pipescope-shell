from setuptools import setup

setup(
    name="pipescope",
    version="0.1.0",
    description="Shell pipeline stage-by-stage debugger",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    py_modules=["pipescope"],
    entry_points={"console_scripts": ["pipescope=pipescope:main"]},
    python_requires=">=3.8",
)
