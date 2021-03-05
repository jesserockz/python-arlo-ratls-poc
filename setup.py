import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt')) as requirements_txt:
    REQUIRES = requirements_txt.read().splitlines()

setup(
    name="python-arlo-ratls-poc",
    version="0.0.1",
    license="MIT",
    url="https://github.com/jesserockz/python-arlo-ratls-poc",
    author="@jesserockz",
    description="Access Arlo Base Station Local storage",
    zip_safe=True,
    install_requires=REQUIRES,
    entry_points={
        'console_scripts': [
            'arlo = arlo.__main__:main'
        ]
    },
    packages=find_packages(include="arlo.*")
)
