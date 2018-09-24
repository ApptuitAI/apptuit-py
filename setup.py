from setuptools import setup

setup(
    name="apptuit",
    packages=['apptuit'],
    version="0.2.3",
    description="Apptuit Python Client",
    url="https://github.com/ApptuitAI/apptuit-py",
    author="Abhinav Upadhyay",
    author_email="abhinav.updadhyay@agiltix.ai",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    install_requires=['pandas', 'numpy', 'requests'],
    data_files=['LICENSE']
)
