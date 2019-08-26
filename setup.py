from setuptools import setup

setup(
    name="apptuit",
    packages=['apptuit', 'apptuit.pyformance'],
    version="2.3.0",
    description="Apptuit Python Client",
    url="https://github.com/ApptuitAI/apptuit-py",
    author="Abhinav Upadhyay",
    author_email="abhinav.updadhyay@agilitix.ai",
    license="Apache License 2.0",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    install_requires=['requests', 'pyformance'],
    tests_require=['mock;python_version<"3.3"', 'nose', 'pandas', 'numpy'],
    test_suite='nose.collector',
    data_files=['LICENSE']
)
