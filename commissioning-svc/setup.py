#!python

from setuptools import find_packages, setup

# fmt: off
setup(
    name='commissioning-svc',
    author_email='michal.lowas-rzechonek@silvair.com',
    description=(
        'Commissioning Service'
    ),
    url='https://github.com/homersoft/caching.git',
    packages=find_packages(exclude=('test*', )),
    include_package_data=True,
    package_data={
        'commissioning': [
            'alembic/**/*',
            'alembic/*',
            'alembic.ini',
        ],
    },
    setup_requires=[
        'pip-pin>=0.0.6',
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
