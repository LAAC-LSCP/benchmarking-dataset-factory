class StepFailedException(Exception):
    """
    Raised when a step in the dataset pipeline fails.
    """

    def __init__(self, step_name: str, message: str = ""):
        self.step_name = step_name
        self.message = message or f"Step '{step_name}' failed."

        super().__init__(self.message)
