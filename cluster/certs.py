class SSLCert:
    def __init__(self, cert_path: str):
        self.__path = cert_path

    def certfile(self) -> str:
        return f"{self.__path}.crt"

    def keyfile(self) -> str:
        return f"{self.__path}.key"

    # should also handle regenerating certs
