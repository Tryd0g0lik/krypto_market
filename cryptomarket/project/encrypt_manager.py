"""
cryptomarket/project/encrypt_manager.py

https://cryptography.io/en/latest/fernet/
"""

from cryptography.fernet import Fernet


class AESEncrypt:
    """
    TODO: создать шифр
        Каждый пользователь имеет индивидуальный ключ
    """

    def __init__(
        self,
    ) -> None:
        self.log_t = "[AESEncrypt.%s]: "

    async def _str_to_encrypt(self, plaintext: str) -> dict[bytes, bytes]:
        """
        :param plaintext: (str) Clean text for encryption.
        :return: asynccontext: Example '{key: encrypted}' or \
            by type '{< bytes_key_generated_Fernet >: <bytes_decrypt_text >}'
        """
        if plaintext is None:
            raise ValueError(
                "%s ERROR => The 'plaintext' is required the variable!",
                (self.log_t % self._str_to_encrypt.__name__),
            )
        if not isinstance(plaintext, str | bytes):
            raise TypeError(
                "%s TypeError => Check a type for the 'plaintext'!",
                (self.log_t % self._str_to_encrypt.__name__),
            )

        key = Fernet.generate_key()
        cipher = Fernet(key)

        secret_text = plaintext.encode() if isinstance(plaintext, str) else plaintext
        encrypted = cipher.encrypt(secret_text)
        return {key: encrypted}

    def _encrypt_to_str(self, encrypted_dict: dict[bytes, bytes]) -> str:
        """
        :param encrypted_dict: (dict[bytes, bytes]) Encrypted dict. Example '{key: encrypted}' or\
            by type '{< bytes_key_generated_Fernet >: <bytes_decrypt_text >}'.
        :return: str
        """
        # Check of type on the  'encrypted_dict' var.
        if not isinstance(encrypted_dict, dict):
            raise TypeError(
                "%s TypeError => Check a type for the 'encrypted_dict'!",
                (self.log_t % self._encrypt_to_str.__name__),
            )
        key_list = list(encrypted_dict.keys())
        value_list = list(encrypted_dict.values())
        # Check of type per a key & value from the  'encrypted_dict' dictionary.
        if (
            key_list[0] is None
            or value_list[0] is None
            or not isinstance(key_list[0], bytes)
            or not isinstance(value_list[0], bytes)
        ):
            raise TypeError(
                "%s TypeError => Check a type for the key and value from the 'encrypted_dict'!",
                (self.log_t % self._encrypt_to_str.__name__),
            )

        cipher = Fernet(key_list[0])
        decrypted: bytes = cipher.decrypt(value_list[0])
        return decrypted.decode()
