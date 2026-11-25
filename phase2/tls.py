"""Separate edge keys, one public CA: only public certificates/CSRs move Macs."""
import os
import shutil
import subprocess
from pathlib import Path

from .config import ROOT, common


def directory():
    folder = ROOT / "phase2/tls"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def anchor():
    file = directory() / "ca.crt"
    if not file.is_file():
        raise ValueError("Missing phase2/tls/ca.crt; create the project CA on Mac 2 and copy only its public certificate to Mac 1")
    return file


def openssl(*args, **kwargs):
    return common.run([common.binary("openssl"), *args], **kwargs)


def create_ca(c):
    folder = directory()
    if (folder / "ca.crt").exists() or (folder / "ca.key").exists():
        raise ValueError("Phase 2 CA already exists; keep it, no silent key/certificate replacement")
    mask = os.umask(0o077)
    try:
        openssl("req", "-x509", "-newkey", "rsa:2048", "-noenc", "-sha256", "-days", "365",
                "-subj", f"/CN={c['TEAM_NAME']} Phase 2 CA", "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-keyout", folder / "ca.key", "-out", folder / "ca.crt")
        (folder / "ca.crt").chmod(0o644)
    finally:
        os.umask(mask)
    print("Created CA. Keep ca.key only on Mac 2; copy ca.crt to Mac 1.")


def csr(c, edge):
    folder = directory() / edge
    folder.mkdir(exist_ok=True)
    if any((folder / name).exists() for name in ("server.key", "server.csr", "server.crt")):
        raise ValueError("Edge key/CSR/certificate already exists; reuse it")
    mask = os.umask(0o077)
    try:
        openssl("req", "-new", "-newkey", "rsa:2048", "-noenc", "-sha256", "-subj", f"/CN={c['APP_DOMAIN']}",
                "-addext", f"subjectAltName=DNS:{c['APP_DOMAIN']},DNS:{c['API_DOMAIN']}",
                "-keyout", folder / "server.key", "-out", folder / "server.csr")
        (folder / "server.csr").chmod(0o644)
    finally:
        os.umask(mask)
    print(f"CSR: {folder / 'server.csr'}. Send only this public CSR to Mac 2 for signing.")


def sign(c, csr_path, output):
    folder = directory()
    output = Path(output)
    if output.exists():
        raise ValueError("Output certificate already exists; refusing overwrite")
    if not (folder / "ca.key").is_file():
        raise ValueError("Signing requires the CA private key on Mac 2")
    extensions = folder / "server-extensions.cnf"
    extensions.write_text(f"basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:{c['APP_DOMAIN']},DNS:{c['API_DOMAIN']}\n")
    openssl("req", "-in", str(csr_path), "-verify", "-noout")
    # Random serial avoids races or shared CA serial files during repeated signing.
    openssl("x509", "-req", "-in", str(csr_path), "-CA", anchor(), "-CAkey", folder / "ca.key",
            "-set_serial", "0x" + os.urandom(16).hex(), "-days", "90", "-sha256", "-extfile", extensions, "-out", output)
    output.chmod(0o644)
    print(f"Signed public certificate: {output}; send it back to the edge owning the matching private key.")


def verify(c, edge):
    folder = directory() / edge
    cert, key = folder / "server.crt", folder / "server.key"
    for name in (c["APP_DOMAIN"], c["API_DOMAIN"]):
        openssl("verify", "-CAfile", anchor(), "-verify_hostname", name, cert)
    a = subprocess.check_output([common.binary("openssl"), "x509", "-in", str(cert), "-pubkey", "-noout"])
    b = subprocess.check_output([common.binary("openssl"), "pkey", "-in", str(key), "-pubout"])
    common.expect(a == b, "Certificate does not match this edge's private key")
    common.expect(key.stat().st_mode & 0o077 == 0, "Private key permissions must be 600 or stricter")
    openssl("x509", "-in", cert, "-noout", "-subject", "-dates", "-fingerprint", "-sha256")
    print("PASS: certificate chain, both SANs, key match, validity and key permissions")
