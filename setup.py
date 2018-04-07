from distutils.core import setup

setup(
    name='PySteam',
    version='0.1.dev',
    packages=['steamapi', ],
    license='MIT License',
    description='Python interface for Steam web chat.',
    #long_description=open('README.txt').read(),

    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
    ],
    install_requires=[
        'requests',
        'pycryptodome',
        'pyee',
        'enum34',
        'pyquery',
        'future',
        'munch'
    ],
    extras_require={
        'test':  ['pytest'],
    },
    keywords='steam web chat',
)

# Install in "editable mode" for development:
# pip install -e .
