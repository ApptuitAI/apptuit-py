from distutils.core import setup

setup(
    name="pyapptuit",
    packages=['apptuit'],
    version="0.1",
    description="Apptuit Python Client",
    author="Abhinav Upadhyay",
    author_email="abhinav.updadhyay@agiltix.ai",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.x",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    long_description=open('README.md').read())

