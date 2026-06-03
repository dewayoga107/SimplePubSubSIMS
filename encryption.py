import base64
import hashlib
import hmac
import json
import os

# Fungsi untuk membuat root key dari master key dan label root.
def create_root_key(master_key: bytes, root_label: str = "") -> bytes:
    """
    Membuat root key untuk Hierarchy Key Tree.
    """

    return hmac.new(
        master_key,
        root_label.encode("utf-8"),
        hashlib.sha256
    ).digest()

# Fungsi untuk menurunkan child key dari parent key menggunakan label child.
def derive_child_key(parent_key: bytes, child_label: str) -> bytes:
    """
    Menurunkan child key dari parent key.
    child_label menggunakan label biner:
    - root: ""
    - anak kiri root: "+0"
    - anak kanan root: "+1"
    """

    return hmac.new(
        parent_key,
        child_label.encode("utf-8"),
        hashlib.sha256
    ).digest()

# Fungsi untuk mengenkripsi payload dictionary menjadi nonce dan ciphertext.
def encrypt_payload(payload: dict, key: bytes) -> dict:
    """
    Mengenkripsi payload dictionary menjadi nonce dan ciphertext. Menggunakan keystream berbasis HMAC-SHA256.
    """

    plaintext = json.dumps(payload, sort_keys=True).encode("utf-8")
    nonce = os.urandom(16)

    keystream = _build_keystream(
        key=key,
        nonce=nonce,
        length=len(plaintext)
    )

    ciphertext = bytes(
        plain_byte ^ key_byte
        for plain_byte, key_byte in zip(plaintext, keystream)
    )

    return {
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
    }

# Fungsi untuk mendekripsi encrypted packet menjadi payload asli.
def decrypt_packet(encrypted_packet: dict, key: bytes) -> dict:
    """
    Mendekripsi encrypted packet menjadi payload asli.
    """

    nonce = base64.b64decode(encrypted_packet["nonce"])
    ciphertext = base64.b64decode(encrypted_packet["ciphertext"])

    keystream = _build_keystream(
        key=key,
        nonce=nonce,
        length=len(ciphertext)
    )

    plaintext = bytes(
        cipher_byte ^ key_byte
        for cipher_byte, key_byte in zip(ciphertext, keystream)
    )

    return json.loads(plaintext.decode("utf-8"))

# Fungsi pembantu untuk membangun keystream berbasis HMAC-SHA256.
def _build_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """
    Membuat keystream sederhana berbasis HMAC-SHA256.
    """

    output = b""
    counter = 0

    while len(output) < length:
        counter_bytes = counter.to_bytes(8, byteorder="big")
        block = hmac.new(
            key,
            nonce + counter_bytes,
            hashlib.sha256
        ).digest()

        output += block
        counter += 1

    return output[:length]
