class ExtractionError(Exception):
    """Exception raised for errors in tool info extraction.

    Attributes:
        tool -- the tool that failed to extract the info
        message -- explanation of the error
    """

    def __init__(self, tool, message="Video Information Extraction Failed"):
        self.tool = tool
        self.message = message
        super().__init__(self.message)

class DownloadError(Exception):
    """Exception raised for errors in downloading.

    Attributes:
        tool -- the tool that failed to download
        message -- explanation of the error
    """

    def __init__(self, tool, message="Download Failed"):
        self.tool = tool
        self.message = message
        super().__init__(self.message)
