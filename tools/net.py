"""Shared network helpers for outbound HTTPS calls made by tools/LLM clients."""

import os
import ssl
import tempfile
from typing import Optional


def use_system_certs() -> bool:
    return os.getenv("USE_SYSTEM_CERTS") == "1"


def system_certs_context() -> ssl.SSLContext:
    """Build an SSLContext that trusts the OS certificate store.

    Some environments (e.g. AV software doing TLS inspection) inject a root
    CA into the OS trust store that certifi's bundled CA list doesn't know
    about, breaking HTTPS calls with CERTIFICATE_VERIFY_FAILED. Controlled by
    the USE_SYSTEM_CERTS=1 env var (see .env.example).
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    return context


_system_ca_bundle_path: Optional[str] = None


def system_certs_ca_file() -> str:
    """Dump the OS trust store to a PEM file, for clients that take a CA file
    instead of an SSLContext (e.g. pymongo's tlsCAFile).

    Reuses the same OS-trusted certs as system_certs_context() above.
    """
    global _system_ca_bundle_path

    if _system_ca_bundle_path is not None and os.path.exists(_system_ca_bundle_path):
        return _system_ca_bundle_path

    der_certs = system_certs_context().get_ca_certs(binary_form=True)
    pem_certs = [ssl.DER_cert_to_PEM_cert(der) for der in der_certs]

    fd, path = tempfile.mkstemp(prefix="system_ca_bundle_", suffix=".pem")
    with os.fdopen(fd, "w") as f:
        f.write("".join(pem_certs))

    _system_ca_bundle_path = path
    return path
