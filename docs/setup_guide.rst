Setup Guide
================

This project uses Pipenv for dependency management and packaging. You can learn about the dependencies looking at the Pipfile at the project root directory. Assuming you have a working version of pip, you can install Pipenv using pip:

.. code-block:: bash

   $ pip install --user pipenv

Pipenv will take care of installing dependencies and creating the virtual environment. Run the following command from the project root directory (where the Pipfile and Pipfile.lock are located):

.. code-block:: bash

   $ pipenv install


You can activate the virtual environment using:

.. code-block:: bash

   $ pipenv shell

Depending on Python versions available on your system you may get an error like:

.. code-block:: bash

   Error: the specified Python version (3.8) is not available on your system. 

It is recommended to install the required Python version using pyenv. You can install pyenv using the instructions at https://github.com/pyenv/pyenv?tab=readme-ov-file#installation.

You may need to reactivate your shell after installing pyenv/pipenv to make sure they are added to the PATH.

Once you have pyenv installed, Pipenv will ask you if you like to use pyenv to install the required Python version. You can say yes and Pipenv will install the required Python version in the virtual environment.
