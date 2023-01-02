#!python

from setuptools import find_packages, setup

# fmt: off
setup(
    name='projects-svc',
    author_email='michal.lowas-rzechonek@silvair.com',
    description=(
        'Projects Service'
    ),
    url='https://github.com/homersoft/caching.git',
    packages=find_packages(exclude=('test*', )),
    include_package_data=True,
    package_data={
        'projects': [
            'alembic/**/*',
            'alembic/*',
            'alembic.ini',
        ],
    },
    setup_requires=[
        'pip-pin>=0.0.8',
    ],
    install_requires=[
        'alembic',
        'asyncpg',
        'fastapi',
        'fastapi_sqlalchemy',
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
