from setuptools import setup
import re

requirements = []
with open('requirements.txt') as f:
  requirements = f.read().splitlines()

readme = ''
with open('README.rst') as f:
    readme = f.read()

extras_require = {
    'voice': ['PyNaCl>=1.3.0,<1.5'],
    'docs': [
        'sphinx==4.0.2',
        'sphinxcontrib_trio==1.1.2',
        'sphinxcontrib-websupport',
    ],
    'speed': [
        'orjson>=3.5.4',
    ]
}

packages = [
    'discord',
    'discord.types',
    'discord.ui',
    'discord.webhook',
    'discord.ext.commands',
    'discord.ext.tasks',
]

setup(name='orion.py',
      author='Benitz Original',
      author_email="benitz@numix.xyz",
      url='https://github.com/Discord-Orion/Orion.py',
      project_urls={
        "Documentation": "https://discordpy.readthedocs.io/en/latest/",
        "Issue tracker": "https://github.com/Discord-Orion/Orion.py/issues",
      },
      version="2.0.0",
      packages=packages,
      license='MIT',
      description='A improved and revived version of the original discord.py',
      long_description=readme,
      long_description_content_type="text/x-rst",
      include_package_data=True,
      install_requires=requirements,
      extras_require=extras_require,
      python_requires='>=3.8.0',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Typing :: Typed',
      ]
)
