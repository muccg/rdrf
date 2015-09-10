.. _security:

Security
========

Application Level Security
--------------------------

RDRF is built on top of Django 1.8.4, the latest LTS ( Long term support) release of Django.
LTS releases get security and data loss fixes applied for a guaranteed period of time ( 3+ years.)

Django itself provides distinct levels of built-in security including:

1. SSL ( Secure Socket Layer) security - all web traffic to and from application is encrypted.

2. CSRF ( Cross-Site Request Forgery ) checking: A method of insuring that man in the middle attacks
( falsifying form submissions for example) are impossible.

3. Login restrictions of all "views"

4. In addition RDRF uses the Django Secure package ( http://django-secure.readthedocs.org/en/v0.1.2/) middleware with
all settings enabled by default.

5. RDRF itself includes a fully configurable permissions layer (role based security model)
which restrict the visibility of forms ( and fields) to specified user groups.

6. Furthermore, RDRF stores identifying patient contact/demographic data in a totally distinct database to any clinical/genetic data.


Notes on Operational Security
-----------------------------

Any deployment of a registry will need to address operational security. This is security relating to the environment in which the software runs,
and cannot be addressed by the software itself.

1. security of data on physical media

The registry framework stores data in PostgreSQL and MongoDB. Thedatabase these systems use should be encrypted.
This ensures that data is protected if the storage hardware is (for example) stolen, reused, or returned to the manufacturer to address a fault.

In this sense, storage includes all physical media which is used to store registry data, including the volumes used by the database software,
the volume on which the front end is installed, and any volumes used for operating system "swap" space.

2. inter-server / inter-datacentre encryption

Communication between the front-end and the databases should be encrypted. This is to guard against confidential data being intercepted "in transit".
In addition to encryption, SSL certificates should be used (and databases and database clients configured to verify them)
so that a third party cannot impersonate the database or a database client (known as a "person in the middle" attack.)

3. encrypted access to front-end

Access to the front-end should be via SSL configured web server. The SSL configuration should be modern (with processes in place to ensure it remains current)
and have all security updates applied. This includes ensuring that a modern cipher suite is selected. Such a cipher suite
will provide perfect forward security, reducing the consequences of a compromise of the server SSL key, while also allowing
use of ciphers which increase client performance.

4. physical security - servers and infrastructure

The servers and related infrastructure should be maintained in a secure location, where the risk of unauthorised access, tampering or theft is
reduced to a minimum. There should be documentation of who can access the facility, and when that access changes.

5. physical security - workstations

Workstations (including laptops) used to access the registry should require user authorisation, be subject to appropriate security policies, and
have appropriate security software installed. On any workstation on which reports may be
downloaded from the registry and stored, whole-disk encryption should be implemented on the device to guard against
the risk of data exposure through theft or accidental loss.