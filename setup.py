from setuptools import setup, find_packages

setup(name='robot',
      version='0.0.1',
      description='task manager module for jetson robot',
      license='MIT',
      author='Olivier Martin',
      author_email='omartin@live.ca',
      install_requires=['paho-mqtt'],
      url='https://github.com/omartin2010/jetson-task-manager',
      packages=find_packages(where='robot'),
      package_dir={'': 'robot'},
      python_requires='>=3.6')
