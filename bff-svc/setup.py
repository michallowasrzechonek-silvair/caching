#!python

from setuptools import find_packages, setup

# fmt: off
setup(
    name='bff-svc',
    author_email='michal.lowas-rzechonek@silvair.com',
    description=(
        'BFF Service',
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
        'yarl',
    ],
    develop_requires=[
        'black',
        'isort',
    ],
    tests_require=[]
)
# fmt: on
