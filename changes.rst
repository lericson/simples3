Changes in simples3 1.0
-----------------------

* Made simples3 a "flat package", imports work as usual.
* Refactored ``url_for`` to ``make_url_authed``, ``make_url``.
* Added an optional timeout argument to the ``S3Bucket`` class.
* Added nose-based testing.
* Added support for streaming with ``poster.streaminghttp``.
* Added support for Google App Engine.

Changes in simples3 0.5
-----------------------

* Add S3-to-S3 copy method.

Changes in simples3 0.4
-----------------------

* Minor fixes, released as 0.4 mostly because the previous version naming
  scheme was a bad idea.
* 0.4.1: Made the put method retry on HTTP 500.
* 0.4.1: Fix a critical error in signature generation when metadata is given.

Changes in simples3 0.3
-----------------------

* Add a ``url_for`` method on buckets which lets you use expiring URLs. Thanks
  to Pavel Repin.
* Much better test coverage.
* ``simples3`` now works on Python 2.6's ``mimetypes`` module.
* r1: Handle HTTP errors in exception parser better, which broke the existence
  test.
