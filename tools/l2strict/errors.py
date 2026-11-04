"""Error types used by the strict pipeline."""


class L2Error(Exception):
    """Base class for expected pipeline failures."""


class DecryptError(L2Error):
    pass


class PackageError(L2Error):
    pass


class BoundsError(PackageError):
    pass


class PropertyError(PackageError):
    pass


class ReferenceError(PackageError):
    pass


class ExtractionError(L2Error):
    pass


class StageError(L2Error):
    pass


class AssetError(L2Error):
    pass


class VerificationError(L2Error):
    pass
