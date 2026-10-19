Changelog
=========

4.0.0 (unreleased)
------------------

First release of the maintained fork of fulfilio/python-magento.

* Published on PyPI as ``magento1-client``; the import name is still
  ``magento``.

* Requires Python 3.9 or later. Python 2 is no longer supported.
* Replace the unmaintained ``suds-jurko`` with ``suds-community>=1.0``.
  ``suds-jurko`` does not build with setuptools 58 or later, so 3.1 no
  longer installs on current Python (fulfilio#30, fulfilio#33).
* Packaging moved from ``setup.py`` to ``pyproject.toml``. ``requests`` is
  now an optional ``rest`` extra.
* Add a test suite (run against a local stand-in for the Magento XML-RPC
  API) and GitHub Actions CI on Python 3.9 to 3.14. The tests confirm every
  documented API (``client.product`` etc.) is available (fulfilio#15).
* README: fix typos and a broken indent in the examples, explain how to check that a
  connection and credentials work (fulfilio#25), document the
  ``product.create`` data format (fulfilio#27), and explain that
  ``order.search`` needs the Fulfil.IO connector extension and is not in
  the stock Magento 1 API (fulfilio#26).
* Add opt-in integration tests against a real OpenMage LTS 20.18 in Docker
  (``dev/openmage``). They are skipped unless ``OPENMAGE_URL`` is set.

3.1 (2019-02-22)
----------------

Last release by Fulfil.IO.
