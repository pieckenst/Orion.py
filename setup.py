from setuptools import setup

requirements = []
README = ''

with open('requirements.txt') as f:
  requirements = f.read().splitlines()

with open('README.rst') as f:
    README = f.read()

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
    'discord.ext.menus',
    'discord.ext.menus.views'
]

setup(name='fusion.py',
      author='Benitz Original',
      author_email="benitz@numix.xyz",
      url='https://github.com/Senarc-Studios/Fusion.py',
      project_urls={
        "Old Documentation": "https://discordpy.readthedocs.io/en/latest/",
        "New Documentation": "https://fusion.senarc.org",
        "Issue tracker": "https://github.com/Senarc-Studios/Fusion.py/issues",
        "Development Branch": "https://github.com/Senarc-Studios/Fusion.py/tree/Development"
      },
      version="2.2.5",
      packages=packages,
      license='MIT',
      description='An API wrapper for discord; maintained and improved from discord.py',
      long_description=README,
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
        'Typing :: Typed'
      ]
)