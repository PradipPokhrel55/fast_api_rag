class RagBackendError(Exception):
    """Base class for domain-specific errors raised by the service layer."""


class UnsupportedFileTypeError(RagBackendError):
    pass


class EmptyDocumentError(RagBackendError):
    pass


class DocumentNotFoundError(RagBackendError):
    pass
