import setuptools

with open('README.md', 'r') as readme:
    long_description = readme.read()

with open('requirements.txt') as reqs:
    requirements = reqs.read().splitlines()

setuptools.setup(
    name='ba_data_paths',
    version='0.6',
    author='Joel McCune',
    author_email='jmccune@esri.com',
    description='ArcGIS Pro Business Analyst data path utilities.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/knu2xs/ba_data_paths',
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Scientific/Engineering :: GIS'
    ]
)
