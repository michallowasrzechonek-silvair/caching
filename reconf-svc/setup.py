#!python

from setuptools import find_packages, setup

# fmt: off
setup(
    name='reconf-svc',
    author_email='michal.lowas-rzechonek@silvair.com',
    description=(
        'Reconfiguration Service',
    ),
    url='https://github.com/homersoft/caching.git',
    packages=find_packages(exclude=('test*', )),
    setup_requires=[
        'pip-pin>=0.0.8',
    ],
    install_requires=[
        'aiohttp',
        'fastapi',
        'uvicorn',
        'watchfiles',
        'yarl',
    ],
    develop_requires=[
        'black',
        'flake8',
        'isort',
        'mypy',
    ],
    tests_require=[]
)
# fmt: on
