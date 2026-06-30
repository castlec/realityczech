# Release verification

Reality Czech currently identifies as version `0.4.0` with Android version code `4`.

Normal debug builds use the cached `reality-czech-main-debug-keystore-v1` certificate so consecutive CI artifacts can update one another. APKs created before that cache was introduced may require one uninstall because Android will reject an update signed by a different certificate.

The manual `Signed Android Release` workflow uses repository secrets and never commits the private release key:

- `REALITY_CZECH_KEYSTORE_BASE64`
- `REALITY_CZECH_KEYSTORE_PASSWORD`
- `REALITY_CZECH_KEY_ALIAS`
- `REALITY_CZECH_KEY_PASSWORD`

A release artifact includes the signed APK and its SHA-256 file. The same keystore and alias must be retained for every future release.
