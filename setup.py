from setuptools import setup
import os
import io


here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(
    name='aiowstunnel',
    description='Persistent and reliable TCP tunneling on websockets '
                'based on asyncio',
    version='0.4.3',
    url='https://github.com/richardbann/aiowstunnel',
    author='Richard Bann',
    author_email='richardbann@gmail.com',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6'
    ],
    keywords='tunneling TCP websocket',
    install_requires=[
        'websockets >= 3.4'
    ],
    package_data={'aiowstunnel': ['resources/static/*/*', 'resources/*.*']},
    license='MIT',
    packages=['aiowstunnel'],
)
