from setuptools import find_packages
from setuptools import setup

with open("requirements.txt") as f:
    content = f.readlines()
requirements = [x.strip() for x in content if "git+" not in x]

setup(name='DumbResearch',
      version="0.0.1",
      description="Desk research automation",
      license="MIT",
      author="Roscoe92",
      author_email="maxpappert4292@gmail.com",
      #url="https://github.com/Roscoe92/DumbResearch",
      install_requires=requirements,
      packages=find_packages(include=["API", "API.*"]),
      # include_package_data: to install data from MANIFEST.in
      include_package_data=True
)
