.. raw:: html

   <!-- PROJECT SHIELDS -->

.. raw:: html

   <!--
   *** I'm using markdown "reference style" links for readability.
   *** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
   *** See the bottom of this document for the declaration of the reference variables
   *** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
   *** https://www.markdownguide.org/basic-syntax/#reference-style-links
   -->

|Contributors| |Forks| |Stargazers| |Issues| |MIT License| |LinkedIn|

.. raw:: html

   <!-- PROJECT LOGO -->
   <br />
    <p align="center">
      <a href="https://github.com/yifan/apihub">
        <img src="https://raw.githubusercontent.com/yifan/apihub/master/images/APIHub.png" alt="Logo" width="600" height="400">
      </a>

      <h3 align="center">APIHub</h3>

      <p align="center">
        APIHub is a platform to dynamically serve API services on-fly. API service workers can be deployed when needed.
        <br />
        <a href="https://github.com/yifan/apihub"><strong>Explore the docs »</strong></a>
        <br />
        <br />
        <a href="https://github.com/yifan/apihub">View Demo</a>
        ·
        <a href="https://github.com/yifan/apihub/issues">Report Bug</a>
        ·
        <a href="https://github.com/yifan/apihub/issues">Request Feature</a>
      </p>
        <br />
        <a href="https://github.com/yifan/apihub"><strong>Explore the docs »</strong></a>
        <br />
        <br />
        <a href="https://github.com/yifan/apihub">View Demo</a>
        ·
        <a href="https://github.com/yifan/apihub/issues">Report Bug</a>
        ·
        <a href="https://github.com/yifan/apihub/issues">Request Feature</a>
      </p>
    </p>

.. raw:: html

   <!-- TABLE OF CONTENTS -->
    <details open="open">
      <summary><h2 style="display: inline-block">Table of Contents</h2></summary>
      <ol>
        <li>
          <a href="#about-the-project">About The Project</a>
          <ul>
            <li><a href="#built-with">Built With</a></li>
          </ul>
        </li>
        <li>
          <a href="#getting-started">Getting Started</a>
          <ul>
            <li><a href="#prerequisites">Prerequisites</a></li>
            <li><a href="#installation">Installation</a></li>
          </ul>
        </li>
        <li><a href="#usage">Usage</a></li>
        <li><a href="#roadmap">Roadmap</a></li>
        <li><a href="#contributing">Contributing</a></li>
        <li><a href="#license">License</a></li>
        <li><a href="#contact">Contact</a></li>
        <li><a href="#acknowledgements">Acknowledgements</a></li>
      </ol>
    </details>


About The Project
=================

`[Product Name Screen
Shot][product-screenshot] <https://raw.githubusercontent.com/yifan/apihub/master/images/APIHub.png>`__

Here’s a blank template to get started: **To avoid retyping too much
info. Do a search and replace with your text editor for the following:**
``yifan``, ``apihub``, ``yifan2019``, ``email``, ``APIHub``,
``project_description``

Features & TODOs
----------------

::

   [X] Security
       [X] authenticate
       [X] admin, manager, user
       [X] user management
       [X] rate limiter
       [ ] register
       [ ] social login
   [ ] Subscription
       [-] subscription
       [-] quota
       [X] application token
       [-] daily usage record in redis
   [ ] Async/sync API calls
       [ ] api worker reports input/output: describe
       [X] generic worker deployment 
       [ ] auto scaler for api workers

Built With
----------

-  `fastapi <https://fastapi.tiangolo.com/>`__
-  `SQLAlchemy <https://www.sqlalchemy.org/>`__
-  `pydantic <https://pydantic-docs.helpmanual.io/>`__
-  `tanbih-pipeline <https://github.com/yifan/pipeline>`__
-  `psycopg2 <https://pypi.org/project/psycopg2/>`__
-  `redis <https://pypi.org/project/redis/>`__
-  `poetry <https://python-poetry.org/>`__

.. raw:: html

   <!-- GETTING STARTED -->

Getting Started
===============

To get a local copy up and running follow these simple steps.

Prerequisites
-------------

This is an example of how to list things you need to use the software
and how to install them.

Installation
------------

1. Clone the repo

   .. code:: sh

      git clone https://github.com/yifan/apihub.git

2. Install python packages

   .. code:: sh

      poetry install

.. raw:: html

   <!-- USAGE EXAMPLES -->

Usage
=====

Use this space to show useful examples of how a project can be used.
Additional screenshots, code examples and demos work well in this space.
You may also link to more resources.

*For more examples, please refer to
the*\ `Documentation <https://example.com>`__

.. raw:: html

   <!-- ROADMAP -->

Roadmap
=======

See the `open issues <https://github.com/yifan/apihub/issues>`__ for a
list of proposed features (and known issues).

.. raw:: html

   <!-- CONTRIBUTING -->

Contributing
============

Contributions are what make the open source community such an amazing
place to be learn, inspire, and create. Any contributions you make are
**greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch
   (``git checkout -b feature/AmazingFeature``)
3. Commit your Changes (``git commit -m 'Add some AmazingFeature'``)
4. Push to the Branch (``git push origin feature/AmazingFeature``)
5. Open a Pull Request

Testing
=======

1. Start postgres and redis

   .. code:: sh

      docker compose up

2. Setup environment variables in a local .env file

   .. code:: sh

      cat >.env <<EOF
      DB_URI="postgresql://dbuser:dbpass@localhost:5432/test"
      JWT_SECRET="nosecret"
      REDIS="redis://localhost:6379/1"
      IN_REDIS="redis://localhost:6379/1"
      OUT_REDIS="redis://localhost:6379/1"
      SECURITY_TOKEN_EXPIRES_DAYS=1
      SUBSCRIPTION_TOKEN_EXPIRES_DAYS=1
      EOF

3. Run tests

   .. code:: sh

      poetry run test

4. Shutdown docker services

   .. code:: sh

      docker compose down

.. raw:: html

   <!-- LICENSE -->

License
=======

Distributed under the MIT License. See ``LICENSE`` for more information.

.. raw:: html

   <!-- CONTACT -->

Contact
=======

Yifan Zhang - [@yifan2019](https://twitter.com/yifan2019) -
yzhang@hbku.edu.qa

Project Link: https://github.com/yifan/apihub

.. raw:: html

   <!-- ACKNOWLEDGEMENTS -->

Acknowledgements
================

-  
-  
-  

Copyright (C) 2021, Qatar Computing Research Institute, HBKU

.. raw:: html

   <!-- MARKDOWN LINKS & IMAGES -->

.. raw:: html

   <!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

.. |Contributors| image:: https://img.shields.io/github/contributors/yifan/apihub.svg?style=for-the-badge
   :target: https://github.com/yifan/apihub/graphs/contributors
.. |Forks| image:: https://img.shields.io/github/forks/yifan/apihub.svg?style=for-the-badge
   :target: https://github.com/yifan/apihub/network/members
.. |Stargazers| image:: https://img.shields.io/github/stars/yifan/apihub.svg?style=for-the-badge
   :target: https://github.com/yifan/apihub/stargazers
.. |Issues| image:: https://img.shields.io/github/issues/yifan/apihub.svg?style=for-the-badge
   :target: https://github.com/yifan/apihub/issues
.. |MIT License| image:: https://img.shields.io/github/license/yifan/apihub.svg?style=for-the-badge
   :target: https://github.com/yifan/apihub/blob/master/LICENSE
.. |LinkedIn| image:: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
   :target: https://linkedin.com/in/yifanzhang
