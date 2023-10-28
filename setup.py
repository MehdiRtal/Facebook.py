from setuptools import setup


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="facebook_py",
    version="0.1",
    packages=["facebook_py"],
    package_dir={"facebook_py": "."},
    install_requires=requirements,
)
