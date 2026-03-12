from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="next_pms",
    version="0.0.1",
    description="IT Project Management System for ERPNext",
    author="EFTPMS",
    author_email="info@eftpms.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
