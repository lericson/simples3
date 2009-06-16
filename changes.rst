Changes in simples3 0.4
-----------------------

 * Minor fixes, released as 0.4 mostly because the previous version naming
   scheme was a bad idea.

Changes in simples3 0.3
-----------------------

 * Add a `url_for` method on buckets which lets you use expiring URLs. Thanks
   t o Pavel Repin.
 * Much better test coverage.
 * `simples3` now works on Python 2.6's `mimetypes` module.
 * r1: Handle HTTP errors in exception parser better, which broke the existence
       test.
