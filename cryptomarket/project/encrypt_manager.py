"""
cryptomarket/project/encrypt_manager.py

https://cryptography.io/en/latest/fernet/
"""

from cryptography.fernet import Fernet

from cryptomarket.errors import EncryptTypeError


class EncryptManager:
    """
    TODO: создать шифр
        Каждый пользователь имеет индивидуальный ключ
    """

    def __init__(
        self,
    ) -> None:
        self.log_t = "[AESEncrypt.%s]: "

    async def str_to_encrypt(self, plaintext: str, *args) -> dict[str, str]:
        """
        :param plaintext: (str) Clean text for encryption.
        :return: asynccontext: Example '{key: encrypted}' or \
            by type '{< key_generated_Fernet >: <decrypt_text >}'
        :return args: This data for recording the 'encrypt_key' to the cache server
        """
        if plaintext is None:
            raise EncryptTypeError(
                "%s ERROR => The 'plaintext' is required the variable!"
                % (self.log_t % self.str_to_encrypt.__name__),
            )
        if not isinstance(plaintext, str | bytes):
            raise EncryptTypeError(
                "%s TypeError the 'plaintext'!"
                % (self.log_t % self.str_to_encrypt.__name__)
            )

        encrypt_key_b = Fernet.generate_key()
        cipher = Fernet(encrypt_key_b)

        secret_text = plaintext.encode() if isinstance(plaintext, str) else plaintext
        encrypted_b = cipher.encrypt(secret_text)
        encrypted = encrypted_b.decode("utf-8")
        encrypt_key = encrypt_key_b.decode("utf-8")
        return {encrypt_key: encrypted}

    def descrypt_to_str(self, encrypted_dict: dict[bytes, bytes]) -> str:
        """
        :param encrypted_dict: (dict[bytes, bytes]) Encrypted dict. Example '{key: encrypted}' or\
            by type '{< bytes_key_generated_Fernet >: <bytes_decrypt_text >}'.
        :return: str
        """
        # Check of type on the  'encrypted_dict' var.
        if not isinstance(encrypted_dict, dict):
            raise EncryptTypeError(
                "%s TypeError the 'encrypted_dict'!"
                % (self.log_t % self.descrypt_to_str.__name__),
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
            raise EncryptTypeError(
                """%s TypeError => Check a type for the key and value from\
             the 'encrypted_dict'!"""
                % (self.log_t % self.descrypt_to_str.__name__)
            )

        cipher = Fernet(key_list[0])
        decrypted: bytes = cipher.decrypt(value_list[0])
        return decrypted.decode()
