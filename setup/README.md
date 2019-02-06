# Setup

Following are instructions and hints for setting up an environment feasible for installing and using the pynhldb framework. 

## Setup of the Python environment

The Python version under which pynhldb was mainly developed is 3.6. The framework ist not prepared as a Python module, i.e. there is no setup routine usable by setuptools or pip. Therefore the necessary non-standard modules (and their dependencies) should be installed separately, e.g. by using pip install module.

These are the additional modules to be installed for using pynhldb:

* [requests](https://pypi.org/project/requests/)
* [python-dateutil](https://pypi.org/project/python-dateutil/)
* [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
* [psycopg2](https://pypi.org/project/psycopg2/)
* [lxml](https://pypi.org/project/lxml/)
* [PyYAML](https://pypi.org/project/PyYAML/)
* [colorama](https://pypi.org/project/colorama/)

To execute the test suite:

* [pytest](https://pypi.org/project/pytest/)

## Setup of the PostgreSQL environment

The PostgreSQL version used for the development of pynhldb is 9.6. Since speficic featured of PostgreSQL (namely array data types) are used it's not possible to use another database system. The installation and configuration of a base PostgreSQL system is out of the scope of this document.

Under the administrative account create a user role `nhl_db` with non-superuser privileges first:

```sql
CREATE ROLE nhl_user LOGIN NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
```

Then create a database `nhl_db` that is owned by the previously created user.

```sql
CREATE DATABASE nhl_db WITH ENCODING='UTF8' OWNER=nhl_user;
```

