"""The default (primary) language of the project.

It is required in every localized data field (``names``, ``description``), it is the
fallback for localized content and UI strings, it must always be built, and ``/index.html``
redirects to it. When changing it, ``locales/<language>.json`` must exist and all localized
data fields must contain the new language.
"""

DEFAULT_LANGUAGE = "de"
