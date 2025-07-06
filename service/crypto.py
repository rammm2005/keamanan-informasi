import base64
import time
from Crypto.Cipher import DES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


class TripleDES:
    def __init__(self, key1: bytes, key2: bytes, key3: bytes):
        self.key1 = key1
        self.key2 = key2
        self.key3 = key3
        self.block_size = DES.block_size
        self.last_encrypt_time = 0.0
        self.last_decrypt_time = 0.0

    def encrypt(self, plaintext: str, mode: str) -> str:
        data = pad(plaintext.encode(), self.block_size)
        iv = get_random_bytes(self.block_size)

        start_time = time.time()

        if mode == 'EDE':
            data = self._encrypt(data, self.key1, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key3, iv)
        elif mode == 'EED':
            data = self._encrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key3, iv)
        elif mode == 'DEE':
            data = self._decrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key3, iv)
        elif mode == 'DED':
            data = self._decrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key3, iv)
        else:
            raise ValueError("Invalid mode")

        self.last_encrypt_time = time.time() - start_time
        print(f"[INFO] Waktu enkripsi ({mode}): {self.last_encrypt_time:.6f} detik")

        return base64.b64encode(iv + data).decode()

    def decrypt(self, ciphertext: str, mode: str) -> str:
        raw = base64.b64decode(ciphertext)
        iv, data = raw[:self.block_size], raw[self.block_size:]

        start_time = time.time()

        if mode == 'EDE':
            data = self._decrypt(data, self.key3, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key1, iv)
        elif mode == 'EED':
            data = self._encrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key1, iv)
        elif mode == 'DEE':
            data = self._decrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key1, iv)
        elif mode == 'DED':
            data = self._encrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key1, iv)
        else:
            raise ValueError("Invalid mode")

        self.last_decrypt_time = time.time() - start_time
        print(f"[INFO] Waktu dekripsi ({mode}): {self.last_decrypt_time:.6f} detik")

        return unpad(data, self.block_size).decode()

    def _encrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        return DES.new(key, DES.MODE_CBC, iv).encrypt(data)

    def _decrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        return DES.new(key, DES.MODE_CBC, iv).decrypt(data)