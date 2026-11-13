# Repository signing keys

archive.asc is the owner GPG public key containing signing subkey
62BBAA20DA6ADFD970C3025A8D7434E6F3E988D9. The matching CI configuration is
GPG_PRIVATE_KEY / GPG_PASSPHRASE secrets and GPG_SIGNING_KEY_FINGERPRINT variable.
The owner replaced s9plus.rsa.pub in both checkouts and APK_PRIVATE_KEY on
GitHub with their RSA key. The unencrypted PKCS#8 PEM header
-----BEGIN PRIVATE KEY----- is supported by OpenSSL and Alpine abuild-sign.

Private keys must never be committed. APK signing derives the public key from
the CI secret and compares it with this checked-in public key before signing.
GitHub does not expose secret values for readback; the actual owner keypair
will be verified by the next Actions build. The old agent-generated
APT_PRIVATE_KEY is no longer referenced by the updated workflows.

Manual dispatch still defaults to artifact-only test builds. Release publishing
remains disabled until the build/signing checks and repository setup finish.
